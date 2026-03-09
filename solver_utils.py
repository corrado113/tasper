import itertools

def latest_start_time(x):
    return x.latest_start_time

def copy_job(job):

    new_job = Job(job.id, job.release_time, job.processing_time, job.value, job.due_date, job.deadline, job.penalty_weight, job.setup_times, job.sta_id, job.E_tx, job.E_idle, job.E_onoff)
    return new_job


class Job:
    def __init__(self, i, r, p, e, dd, dl, w, s, s_i, E_tx, E_idle, E_onoff):
        self.id = i
        self.release_time = r
        self.processing_time = p
        self.value = e
        self.due_date = dd
        self.deadline = dl
        self.penalty_weight = w
        self.setup_times = s
        self.sta_id = s_i
        self.E_tx = E_tx
        self.E_idle = E_idle
        self.E_onoff = E_onoff
        self.latest_start_time = self.deadline - self.processing_time 
        self.best_path = None
        self.path_points = {}  # {job_state.as_key: {start_time: path_point}}
        self.successors = {}  # {window.start_time: [Job, sorted by setup time]}
        self.far_offs = {}  # same as successors but only those far in the future
        self.windows = []  # list of windows sorted by window start time
        self.pretty = ("  [{0}-" + "--{1}-" + "--|{2}|-" + "--{3}]  ({4} - {5}*T)").format(self.release_time,
                                                                                           self.processing_time,
                                                                                           self.due_date, self.deadline,
                                                                                           self.value,
                                                                                           self.penalty_weight)

    def __lt__(self, other):
        if self.release_time != other.release_time:
            return self.release_time < other.release_time
        if self.deadline != other.deadline:
            return self.deadline < other.deadline
        return self.id < other.id

    def __repr__(self):
        return str(self.id)

    def get_job_states(self, size, job_states):  # functional
        return [job_states[key] for key in self.path_points if
                key in job_states and len(job_states[key].job_ids) == size]

    def setup_time(self, successor):  # functional
        return self.setup_times[successor.id]

    def get_path_points(self, job_state, window):  # functional
        return [(time, path_point) for time, path_point in self.path_points[job_state.as_key()].items()
                if
                time - self.processing_time >= window.start_time and time - self.processing_time < window.next_start_time]

    def get_best_path(self):
        value = 0
        path = None
        for job_state in self.path_points:
            for point in self.path_points[job_state].values():
                if point.value > value:
                    path, value = point, point.value
        return path


class Window:
    def __init__(self, start_time, next_start_time, jobs):
        self.start_time = start_time
        self.next_start_time = next_start_time
        self.jobs = jobs
        self.job_ids = sorted([job.id for job in self.jobs])
        self.width = len(jobs)

    def __repr__(self):
        return "[{0}\t{1})".format(self.start_time, self.next_start_time)


class JobState:
    __slots__ = ('job_ids', 'key')

    def __init__(self, job_ids):
        self.job_ids = job_ids
        self.key = ",".join([str(job_id) for job_id in self.job_ids])

    def __len__(self):
        return self.size

    def __repr__(self):
        return "(" + self.as_key() + ")"

    def as_key(self):
        return self.key

    def subsets(self, i):
        return set(itertools.combinations(self.job_ids, i))


class PathPoint:
    __slots__ = (
    'value', 'job', 'previous', 'must_visit', 'VisitedStates', 'path_point_time', 'job_state', 'point_start_time',
    'index')

    def __init__(self, value, job, previous, must_visit, VisitedStates, path_point_time, job_state, index):
        self.value = value
        self.job = job
        self.previous = previous
        self.must_visit = must_visit
        self.VisitedStates = VisitedStates
        self.job_state = job_state
        self.path_point_time = path_point_time
        self.point_start_time = self.path_point_time - job.processing_time
        self.index = index  # Current max index

    def __repr__(self):
        return "(" + str(self.value) + ")"

    def get_path(self):
        if self.previous is None:
            return [self.job]
        else:
            return self.previous.get_path() + [self.job]

    def must_visits(self):
        if self.previous is None:
            return self.must_visit
        else:
            return self.must_visit | (self.previous.must_visits() - {self.job})


def dataset(n, t, r, i):  # functional
    folder = "Dataset_OAS/{0}orders".format(n) + "/Tao{0}".format(t) + "/R{0}".format(r)
    file = "/Dataslack_{0}orders_Tao{1}R{2}_{3}.txt".format(n, t, r, i)
    return folder + file


def line_to_ints(line):  # functional
    return [int(i) for i in line.split(",")]


def line_to_floats(line):  # functional
    return [float(i) for i in line.split(",")]


def extract_jobs(dataset, heuristic_function = latest_start_time):  # functional
    file = open(dataset, "r")
    r = line_to_ints(file.readline())
    p = line_to_ints(file.readline())
    dd = line_to_ints(file.readline())
    dl = line_to_ints(file.readline())
    e = line_to_floats(file.readline())
    w = line_to_floats(file.readline())
    s_id = line_to_ints(file.readline())
    E_tx = line_to_floats(file.readline())  # 232mA
    E_idle = line_to_floats(file.readline())  #
    E_onoff = line_to_floats(file.readline())  #
    s = []
    # print(len(r))
    # for i in range(0, len(r)):
    #     a = file.readline()
    #     s.append(line_to_ints(a))

    jobs = []
    for i in range(0, len(r)):
        # job = Job(i, r[i], p[i], e[i], dd[i], dl[i], w[i], s[i], s_id[i], E_tx[i], E_idle[i], E_onoff[i])
        job = Job(i, r[i], p[i], e[i], dd[i], dl[i], w[i], [0] * len(r), s_id[i], E_tx[i], E_idle[i], E_onoff[i])


        jobs.append(job)

    # Move sink to the end so it won't be inserted inbetween
    jobs[-1].release_time = jobs[-1].deadline
    jobs[-1].due_date = jobs[-1].deadline
    jobs[-1].latest_start_time = jobs[-1].deadline
    jobs[-1].deadline += 1  # algorithm never completes on deadline

    # Calculate index
    index_jobs = [];
    index_jobs = sorted(jobs, key=heuristic_function)
    for i in range(0, len(index_jobs)):
        index_jobs[i].index = i

    # Start path at source
    source_job_state = JobState([jobs[0].id])
    jobs[0].path_points[source_job_state.as_key()] = {}
    source_path_point = PathPoint(jobs[0].value, jobs[0], None, set(), set(), 0, source_job_state, index=0)
    jobs[0].path_points[source_job_state.as_key()][jobs[0].release_time] = source_path_point

    return (jobs, jobs[0], jobs[-1])






def get_time_windows(jobs):  # functional
    time_points = []
    for job in jobs:
        time_points.append(job.release_time)
        if job.processing_time > 0:
            time_points.append(job.latest_start_time + 1)
    time_points = sorted(list(set(time_points)))  # only keep unique entries and sort

    time_windows = []
    for i in range(0, len(time_points) - 1):
        window_start_time = time_points[i]
        next_window_start_time = time_points[i + 1]
        window_jobs = [job for job in jobs if
                       window_start_time >= job.release_time and
                       window_start_time <= job.latest_start_time]
        time_window = Window(window_start_time, next_window_start_time, window_jobs)
        time_windows.append(time_window)

    return time_windows


def list_to_csv(x):
    string = ''
    for el in x:
        string = string + str(el) + '#'
    string = string[:-1]
    return string