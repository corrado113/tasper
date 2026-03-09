#Source code of the neighbourhood heuristic method similar to the Balas-Simonetti neighbourhood. 
#Authors: Mathijs de Weerdt (M.M.deWeerdt@tudelft.nl), Robert Baart, Lei He
#Date: Sept 24, 2020
import copy
import itertools
import math
import time
import gc
import heapq
from csv import writer
from solver_utils import *


class Solver:
    def __init__(self, dataset_file, w=100, heuristic=False, heuristic_function=None, limit=3600, forced_job_list = None):

        # Load problem
        if(forced_job_list is None):
        #if (False):
            self.jobs, self.source, self.sink = extract_jobs(dataset_file,heuristic_function)
        else:
            # _, self.source, self.sink = extract_jobs(dataset_file, heuristic_function)
            self.source = forced_job_list[0]
            self.sink = forced_job_list[-1]
            self.jobs = forced_job_list
            self.jobs.sort(key = lambda x:x.id)
        # Create time windows
        self.time_windows = get_time_windows(sorted(self.jobs))
        self.last_window = self.time_windows[0]
        self.last_partial_job_ids = []
        self.last_prev_job_state = []
        self.priority_queue = []
        self.entry_finder = {}               # mapping of tasks to entries
        self.REMOVED = '<removed-task>'      # placeholder for a removed task
        self.counter = itertools.count()     # unique sequence count

        # Create job state store to avoid duplicates in memory
        self.job_states = {'0': JobState([self.jobs[0].id])}
        
        self.heuristic = heuristic

        self.w = w
        self.w2 = w
        self.limit= limit

        self.heuristic_function = heuristic_function

        self.prep_windows()

        self.normalize = True

        if(self.normalize):
            tx_energy = list()
            vals = list()
            weights = list()
            for job in self.jobs:
                tx_energy.append(job.processing_time * job.E_tx)
                vals.append(job.value)
                weights.append(job.penalty_weight)

            tx_consumption_max = max(tx_energy)

            self.consumption_max = tx_consumption_max + self.jobs[1].E_onoff
            self.consumption_min = 0
            self.val_max = max(vals)
            self.val_min = min(vals)
            self.weight_max = max(weights)
            self.weight_min = min(weights)
            self.rew_max = max((1-self.weight_max), (1-self.weight_min))
            self.rew_min = min( - self.weight_max * self.consumption_max , - self.weight_min * self.consumption_max)

        self.verbose = False
        
    def solve_exact(self):
        t=time.time()
        timeout = False
        if self.verbose:
            for window in self.time_windows:
                print("{0}".format("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"[window.width]), end="")
            print()

        for key in self.source.path_points:
            for time1, path_point in self.source.path_points[key].items():
                self.add_point(path_point)
        for window in self.time_windows:
            self.y = 0
            self.n = 0
            
            if window.id > 0:
                rem_jobs = [j for j in self.time_windows[window.id - 1].jobs if j not in window.jobs]
                for job in rem_jobs:
                    job.path_points = {}
                    toss = []
                    for key in self.job_states:
                        if job.id in self.job_states[key].job_ids:
                            toss.append(key)
                    for key in toss:
                        del(self.job_states[key])
                if len(rem_jobs) > 0:
                    gc.collect()

            while not self.is_empty():
                if time.time()-t>self.limit:
                    timeout = True
                    break
            
                path_point = self.peek_point()
                job = path_point.job
                job_state = path_point.job_state
                path_point_time = path_point.path_point_time

                if path_point.path_point_time-path_point.job.processing_time >= window.next_start_time:
                    break

                if not self.is_dominated(job, job_state, path_point_time, path_point, window):
                    for successor in job.successors[window.start_time]:
                        if time.time()-t>self.limit:
                             timeout = True
                             break                
                        if successor.id not in job_state.job_ids:
                             new_point,get = self.try_path(job, successor, path_point_time, path_point, job_state, window)
                             if get:
                                 self.add_point(new_point)

                    #far off
                    for successor in job.far_offs[window.start_time]:
                        if time.time()-t>self.limit:
                             timeout = True
                             break
                        if successor.id not in job_state.job_ids:
                             new_point,get = self.try_path(job, successor, path_point_time, path_point, job_state, window)
                             if get:
                                self.add_point(new_point)

                else:
                    try:
                        del(job.path_points[job_state.as_key()][path_point_time])
                        del(path_point)
                    except:
                        print("cannot delete path points: job_state = " + str(job_state.job_ids) + " path_point_time = " + str(path_point_time))
                
                self.pop_point()

            if timeout:
                break
            
        return self.sink.get_best_path()
    
    def add_point(self,point):
        if point in self.entry_finder:
            raise KeyError('point already exists')

        count = next(self.counter)
        entry = [point.point_start_time, count, point]
        self.entry_finder[point] = entry
        heapq.heappush(self.priority_queue, entry)

    def remove_point(self,point):
        try:
            entry = self.entry_finder[point]
            entry[-1] = self.REMOVED
            del self.entry_finder[point]
        except:
            pass
            #print("remove unexisting point")

    def peek_point(self):
            while self.priority_queue:
                priority, count, point = self.priority_queue[0]
                if point is not self.REMOVED:
                    return point
                else:
                    heapq.heappop(self.priority_queue)
            raise KeyError('peek from an empty priority queue')

    def pop_point(self):
        while self.priority_queue:
            priority, count, point = heapq.heappop(self.priority_queue)
            if point is not self.REMOVED:
                del self.entry_finder[point]
                return point
        raise KeyError('pop from an empty priority queue')

    def is_empty(self):
        while self.priority_queue:
            priority, count, point = self.priority_queue[0]
            if point is not self.REMOVED:
                return 0
            else:
                heapq.heappop(self.priority_queue)
        return 1

    def is_dominated(self, job, job_state, point_time, point, window):
        start_time = point_time
        value = point.value
        if len(job_state.job_ids)>0:
            for subset in job_state.subsets(len(job_state.job_ids)-1):
                subset_key = JobState(subset).as_key()
                if subset_key in job.path_points:
                    for other_point_time, other_point in job.path_points[subset_key].items():
                        if other_point.value >= value and other_point_time <= start_time:
                            return True
        
        if point.previous is not None:
            swapped_job = point.previous.job
            visited = point.must_visits()
            for alt_job in [job for job in window.jobs if job.id not in job_state.job_ids and job not in visited]:
                ids = sorted([j for j in job_state.job_ids if j != swapped_job.id] + [alt_job.id])
                alt_state = JobState(ids)
                alt_state_key = alt_state.as_key()
                if alt_state_key in job.path_points:
                    for other_point_time, other_point in job.path_points[alt_state_key].items():
                        if other_point.value > value and other_point_time <= start_time or other_point.value >= value and other_point_time < start_time:
                            point.must_visit.add(alt_job)
                            break
            for alt_job in [job for job in window.jobs if job.id not in job_state.job_ids and job not in visited and job not in point.must_visit]:
                ids=sorted(job_state.job_ids + [alt_job.id])
                alt_state = JobState(ids)
                alt_state_key = alt_state.as_key()
                if alt_state_key in job.path_points:
                    for other_point_time, other_point in job.path_points[alt_state_key].items():
                        if other_point.value > value and other_point_time <= start_time or other_point.value >= value and other_point_time < start_time:
                            point.must_visit.add(alt_job)
                            break

        must_visits = sorted(list(point.must_visits()), key=lambda j: j.deadline)

        t = start_time
        for i in range(len(must_visits)):
            if t > must_visits[i].latest_start_time:
                self.y += 1

                return True
            t += must_visits[i].processing_time
            t += min([min(mv.setup_times) for mv in must_visits])
        self.n += 1
        return False
    
    """
    Given a job, a successor job, a starting path point and a job state, sees if a new path
    point in the successor job is feasible, not dominated and if so inserts it.
    """
    def try_path(self, job, successor, path_point_time, path_point, job_state, original_window): 

        temp_point = PathPoint(0, successor, path_point, set(),path_point.VisitedStates,0,path_point.job_state,0)

        #apply balas neighbourhood
        if successor.index + self.w < path_point.index: # successor must be scheduled before path_point
            return temp_point,False

        arrival_time = path_point_time# + job.processing_time
        start_time = max(arrival_time, successor.release_time) + job.setup_time(successor)
        completion_time = start_time + successor.processing_time

        
        # check feasibility of new path point
        if completion_time > successor.deadline:
            return temp_point,False
        
        # calculate value

        succ_val = successor.value

        if self.normalize:
            succ_val = (succ_val - self.val_min) / (self.val_max - self.val_min)

        full_value = path_point.value #+ succ_val
        if(job.sta_id != successor.sta_id):
            energy_consumption = successor.E_tx * successor.processing_time + successor.E_onoff
        else:
            energy_consumption = successor.E_tx * successor.processing_time + min(successor.E_idle * max(successor.release_time - arrival_time,0), successor.E_onoff)


        w = successor.penalty_weight
        if self.normalize:
            energy_consumption =  energy_consumption / self.consumption_max

        value = full_value + ( (1-w) * succ_val + w * (1-energy_consumption))
        
        # calculate new job state
        # see if window is the same as last time, saves looking it up
        partial_job_com_ids,partial_job_ids = self.get_partial_job_state(completion_time, successor, job_state, original_window, path_point)
        if successor.latest_start_time>=completion_time:
            partial_job_com_ids.add(successor.id)
            partial_job_ids.append(successor.id)

        job_ids = sorted(partial_job_ids)
 
        new_job_state = JobState(job_ids)
        new_key = new_job_state.as_key()

        #Calculate current max index
        index = max(path_point.index,successor.index)
        
        # Create new state if completely new
        if new_key not in self.job_states:
            self.job_states[new_key] = new_job_state
        
        new_job_state = self.job_states[new_key]

        # If the state is new even just in this job, no need to check for domination
        if new_key not in successor.path_points:
            successor.path_points[new_key] = {}
            successor.path_points[new_key][completion_time] = PathPoint(value, successor, path_point, set(),partial_job_com_ids,completion_time,new_job_state,index)
            return successor.path_points[new_key][completion_time],True

        # check for dominating path_point for the same state (irrespective of windows!)
        for point_time, point in successor.path_points[new_key].items():
            if point_time <= completion_time and point.value >= value:
                return temp_point,False
            

        # Delete path points dominated by this new one
        toss = []
        for point_time, point in successor.path_points[new_key].items():
            if point.value <= value and point_time >= completion_time:
                toss.append(point_time)
        for point_time in toss:
            point = successor.path_points[new_key][point_time]
            self.remove_point(point)
            del(successor.path_points[new_key][point_time])
            del(point)

        successor.path_points[new_key][completion_time] = PathPoint(value, successor, path_point, set(),partial_job_com_ids,completion_time,new_job_state,index)
        return successor.path_points[new_key][completion_time],True
        
    """
    Finds the time window corresponding to a given time.
    MUTATING: self.last_window
    """
    def get_partial_job_state(self, time, job, job_state, original_window, path_point):
        last_partial_job_com_ids=set()
        self.last_partial_job_ids=[]
        for id in path_point.VisitedStates:
            if self.jobs[id].latest_start_time>=time:
                last_partial_job_com_ids.add(id)
                if self.jobs[id].latest_start_time>=time+job.setup_time(self.jobs[id]) and abs(self.jobs[id].index -job.index) <= self.w:
                    self.last_partial_job_ids.append(id);
        return last_partial_job_com_ids,self.last_partial_job_ids
    
    """
    Finds potential successors for a job completed in a time window which
    """
    def get_suitable_successors(self, job, window, job_state): #functional
        return [job for job in job.successors[window.start_time] if job.id not in job_state.job_ids]

    def prep_windows(self):
        # Store time window index in each time window
        for i in range(0, len(self.time_windows)):
            self.time_windows[i].id = i
        # Store static info in each job about its time windows and successors
        for window in self.time_windows:
            for job in window.jobs:
                    successors = sorted([successor for successor in self.jobs
                                      # jobs that are reachable
                                      if max(successor.release_time, window.start_time + job.processing_time) + job.setup_time(successor) 
                                      <= successor.latest_start_time
                                      # and are not so far in the future that only the highest value path point is significant
                                      and not min(window.next_start_time - 1, job.latest_start_time) + job.processing_time 
                                      <= successor.release_time
                                      # Apply balas neighborhood 
                                     and (abs(successor.index -job.index) <= self.w or successor.index==len(self.jobs)-1 or job.index==0)
                                     ], key=lambda s: job.setup_time(s))
                    far_offs = sorted([successor for successor in self.jobs
                                    # jobs that are so far in the future that only the highest value path point is significant
                                    if min(window.next_start_time - 1, job.latest_start_time) + job.processing_time 
                                    <= successor.release_time
                                    # Apply balas neighborhood 
                                     and (abs(successor.index -job.index) <= self.w or successor.index==len(self.jobs)-1 or job.index==0)
                                   ], key=lambda s: s.release_time + job.setup_time(s))
                    job.successors[window.start_time] = successors
                    job.far_offs[window.start_time] = far_offs
                    job.windows.append(window)
            self.sink.successors[window.start_time] = []    
            
def latest_start_time(x):
    return x.latest_start_time
    

def solver_run(sim_id = 0, n_sta = 16, returns_scheduling = True, options = None, verbose = False, external_job_list = None):
    heuristic_function = latest_start_time
    if(options is None):
        n = 100
        n_slots = 100
        interbeacon_time = 102.4 #ms
        null_deadline = 104 # ms
        time_shift = 2 #ms
        energy_trick = True
        selected_wh = [11]
    else:
        n = options["n"]
        n_slots = options["n_slots"]
        interbeacon_time = options["interbeacon_time"]  # ms
        null_deadline = options["null_deadline"]  # ms
        time_shift = options["time_shift"]  # ms
        selected_wh = options["wh"]
    slot_duration = interbeacon_time / n_slots

    for wh in selected_wh:
      for R in [1]:
        for w in [3]:
             for ins in range(0, 1):
                 filename="test_instance.txt"

                 if (external_job_list is None):
                     job_list, _, _ = extract_jobs(filename, heuristic_function)
                     solver = Solver(filename, heuristic=True, w=wh, heuristic_function=heuristic_function, limit=1800)

                 else:
                     job_list = external_job_list
                     solver = Solver(filename, heuristic=True, w=wh, heuristic_function=heuristic_function, limit=1800, forced_job_list=job_list)

                 tx_energy = list()
                 vals = list()
                 weights = list()
                 for job in job_list:
                     tx_energy.append(job.processing_time * job.E_tx)
                     vals.append(job.value)
                     weights.append(job.penalty_weight)


                 tx_consumption_max = max(tx_energy)
                 consumption_max = tx_consumption_max + job_list[1].E_onoff
                 val_max = max(vals)
                 val_min = min(vals)
                 weight_max = max(weights)
                 weight_min = min(weights)


                 t = -time.time()
                 path = solver.solve_exact()
                 t += time.time()

                 now = path

                 scheduled_jobs = list()
                 while True:
                    if(now):
                        scheduled_jobs.append([now.job, now.point_start_time, now.path_point_time, now.job.sta_id, now.job.release_time, now.job.processing_time, now.job.deadline])
                        now = now.previous
                    else:
                        break

                 scheduled_jobs.reverse()

                 if(verbose):
                     print("Scheduled Jobs:", len(scheduled_jobs) - 2)
                     for job in scheduled_jobs:
                         print("id:{0}\tst:{1}\tend:{2}\tsta:{3}\trel:{4}\tproc:{5}\tdeadl:{6}".format(job[0], job[1], job[2],
                                                                                                       job[3], job[4], job[5],
                                                                                                       job[6]))





                 if returns_scheduling:
                     return scheduled_jobs

                 else:
                     if (energy_trick):
                         print("--------------------------------ENERGY OPTIMIZATION--------------------------------")
                         prev_job = scheduled_jobs[0]
                         jobs_in_a_row = 0
                         for k in range(1, len(scheduled_jobs)):
                             curr_job = scheduled_jobs[k]
                             if curr_job[3] == prev_job[3]:
                                 jobs_in_a_row = jobs_in_a_row + 1
                             else:
                                 for j in range(jobs_in_a_row):
                                     time_diff = scheduled_jobs[k - 1 - j][1] - scheduled_jobs[k - 2 - j][2]
                                     scheduled_jobs[k - 2 - j][2] = min(scheduled_jobs[k - 2 - j][2] + time_diff,
                                                                        scheduled_jobs[k - 2 - j][0].deadline)
                                     scheduled_jobs[k - 2 - j][1] = scheduled_jobs[k - 2 - j][2] - \
                                                                    scheduled_jobs[k - 2 - j][0].processing_time
                                 jobs_in_a_row = 0
                             prev_job = scheduled_jobs[k]

                     if(verbose):
                         for job in scheduled_jobs:
                             print("id:{0}\tst:{1}\tend:{2}\tsta:{3}\trel:{4}\tproc:{5}\tdeadl:{6}".format(job[0], job[1],
                                                                                                           job[2],
                                                                                                           job[3], job[4],
                                                                                                           job[5],
                                                                                                           job[6]))
                     total_reward = 0
                     total_value = 0
                     total_energy = 0
                     total_energy_real = 0
                     real_energy = 0



                     for k in range(1,len(scheduled_jobs)):

                         job = scheduled_jobs[k]

                         val = job[0].value
                         val = (val - val_min) / (val_max - val_min)

                         if (job[0].sta_id != scheduled_jobs[k-1][0].sta_id):
                             energy_consumption = job[0].E_tx * job[0].processing_time + job[0].E_onoff
                         else:
                             energy_consumption = job[0].E_tx * job[0].processing_time + min(
                                 job[0].E_idle * max(job[0].release_time - scheduled_jobs[k-1][2], 0), job[0].E_onoff)

                         w = job[0].penalty_weight

                         energy_consumption_norm = energy_consumption / consumption_max
                         total_value = total_value + val
                         total_energy = total_energy + energy_consumption_norm
                         total_energy_real = total_energy_real + energy_consumption
                         total_reward = total_reward + ((1 - w) * val + w * (1-energy_consumption_norm))


                     print("Energy (Numerical-Norm):",total_energy)
                     print("Energy (Numerical):", total_energy_real)
                     print("Energy (Joule):", total_energy_real * slot_duration)
                     print("Value",total_value)
                     print("Reward",total_reward)
                     print("Energy Efficiency", total_energy_real * slot_duration / (len(scheduled_jobs)-2))
                     try:
                         print("{0}\t{1},{2},{3}\t{4}\t{5}\t{6}".format(wh,n, w, R, ins, path.value, t))
                     except Exception as e:
                         print(e)
                         print("{0},{1},{2},{3}\tNo result.".format(n, w, R, ins))

                     del(solver)
                     del(path)
                     gc.collect()
                     policy_name = "Balas" + str(wh)

                     t0 = list()
                     t1 = list()
                     duration = list()
                     deadline = list()

                     job_ids = list()

                     for job in scheduled_jobs[1:-1]:
                         t0.append(job[4] * slot_duration + time_shift)
                         t1.append((job[1]) * slot_duration + time_shift)
                         duration.append(job[0].processing_time * slot_duration)
                         deadline.append((job[0].deadline) * slot_duration + time_shift)
                         job_ids.append(job[0].id)

                     for k in range(len(t0), n_sta):
                         t0.append(null_deadline)
                         t1.append(null_deadline)
                         duration.append(1)
                         deadline.append(null_deadline)
                         job_ids.append(-1)


                     string_to_csv = ["x", policy_name, list_to_csv(t0), list_to_csv(t1), list_to_csv(duration),
                                      list_to_csv(deadline)]
                     string_to_csv_extra = ["x", policy_name, list_to_csv(t0), list_to_csv(t1), list_to_csv(duration),
                                            list_to_csv(deadline), list_to_csv(job_ids)]
                     print(string_to_csv)
                     with open('TWT_results.csv', 'a+', newline='') as f_object:

                         # Pass this file object to csv.writer()
                         # and get a writer object
                         writer_object = writer(f_object)

                         # Pass the list as an argument into
                         # the writerow()

                         writer_object.writerow(string_to_csv)

                         # Close the file object
                         f_object.close()

                     with open('TWT_results_with_ids.csv', 'a+', newline='') as f_object:

                         # Pass this file object to csv.writer()
                         # and get a writer object
                         writer_object = writer(f_object)

                         # Pass the list as an argument into
                         # the writerow()

                         writer_object.writerow(string_to_csv_extra)

                         # Close the file object
                         f_object.close()
                     sim_id = sim_id + 1

if __name__ == "__main__":
    solver_run(returns_scheduling=False, verbose=True)

