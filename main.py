from pyomo.environ import *
from pyomo.gdp import *
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

# Machines in the factory and their working hours
machines = ['LaserCutter', 'CNC_Mill', 'PaintStation']

# Daily working hours (in 24-hour format)
calendar = {
    'LaserCutter': list(range(480, 1021 , 60)),    # 8 AM to 5 PM
    'CNC_Mill': list(range(480, 961 , 60)),       # 8 AM to 4 PM
    'PaintStation': list(range(540, 1081 , 60))    # 9 AM to 6 PM
}

# Jobs with tasks (job_id, task_id, machine, duration_in_hours, predecessor_task_id)
tasks = [
    ('Job1', 'Cutting', 'LaserCutter', 3, None),
    ('Job1', 'Milling', 'CNC_Mill', 2, 'Cutting'),
    ('Job1', 'Painting', 'PaintStation', 1, 'Milling'),

    ('Job2', 'Cutting', 'LaserCutter', 2, None),
    ('Job2', 'Painting', 'PaintStation', 1, 'Cutting'),

    ('Job3', 'Milling', 'CNC_Mill', 4, None),
    ('Job3', 'Painting', 'PaintStation', 2, 'Milling')
]


Job_Task = {}

for job_id, task_id, machine, duration, predecessor in tasks:
    Job_Task[(job_id, task_id)] = {
        'machine': machine,
        'duration': duration * 60,
        'predecessor': predecessor
    }

# print(Job_Task)
# print(list(range(480, 1020 , 60)))

model = ConcreteModel()
model.Machines = Set(initialize = machines)
model.JobToTask = Set(dimen = 2 , initialize = Job_Task.keys())

model.taskMachine = Param(model.JobToTask, initialize = { (job_id, task_id): data['machine'] for (job_id, task_id), data in Job_Task.items()}, domain = Any)
model.taskDuration = Param(model.JobToTask, initialize = { (job_id, task_id): data['duration'] for (job_id, task_id), data in Job_Task.items() }, domain = Any)
model.taskPredecessor = Param(model.JobToTask, initialize = { (job_id, task_id): data['predecessor'] for (job_id, task_id), data in Job_Task.items() }, domain = Any)
model.machineCalendar = Param(model.Machines, initialize = calendar , domain = Any)
model.taskOnMachine = Param(model.Machines, initialize = {machine: [task for task in model.JobToTask if model.taskMachine[task] == machine] for machine in machines}, domain=Any)


UB = 1440 * 10  

model.startTime = Var(model.JobToTask, domain=NonNegativeReals, bounds=(0, UB))
model.endTime = Var(model.JobToTask, domain=NonNegativeReals, bounds=(0, UB))
model.makespan = Var(domain=NonNegativeReals, bounds=(0, UB))


def task_duration_rule(model, job , task):
    return model.endTime[job, task]  ==  model.startTime[job, task] + model.taskDuration[job, task]

model.taskDurationConstraint = Constraint(model.JobToTask, rule=task_duration_rule)

def precedence_rule(model, job, task):
    predecessor = model.taskPredecessor[job, task]
    if predecessor is None:
        return Constraint.Skip
    else:
        return model.startTime[job, task] >= model.endTime[job, predecessor]

model.taskPredecessorConstraint = Constraint(model.JobToTask, rule=precedence_rule)



overlap_pairs = []
for (j1, t1) in model.JobToTask:
    for (j2, t2) in model.JobToTask:
        if (j1, t1) < (j2, t2):
            if model.taskMachine[(j1, t1)] == model.taskMachine[(j2, t2)]:
                overlap_pairs.append(((j1, t1), (j2, t2)))

def A_before_B_rule(disj, j1, t1, j2, t2):
    disj.c = Constraint(expr= model.startTime[j2, t2] >= model.endTime[j1, t1])

def B_before_A_rule(disj, j1, t1, j2, t2):
    disj.c = Constraint(expr= model.startTime[j1, t1] >= model.endTime[j2, t2])

model.A_before_B = Disjunct(overlap_pairs, rule=A_before_B_rule)
model.B_before_A = Disjunct(overlap_pairs, rule=B_before_A_rule)

model.no_overlap_disjunction = Disjunction(
    overlap_pairs,
    rule=lambda m, j1, t1, j2, t2: [
        m.A_before_B[j1, t1, j2, t2],
        m.B_before_A[j1, t1, j2, t2]
    ]
)

def calendar_start_constraint(model, job, task):
    mach = model.taskMachine[job, task]
    earliest = min(calendar[mach])
    latest = max(calendar[mach])
    return inequality(earliest, model.startTime[job, task], latest)

def calendar_end_constraint(model, job, task):
    mach = model.taskMachine[job, task]
    earliest = min(calendar[mach])
    latest = max(calendar[mach])
    return inequality(earliest, model.endTime[job, task], latest)

model.calendarStartConstraint = Constraint(model.JobToTask, rule=calendar_start_constraint)
model.calendarEndConstraint = Constraint(model.JobToTask, rule=calendar_end_constraint)

def makespan_rule(model, job, task):
    return model.makespan >= model.endTime[job, task]
model.makespanConstraint = Constraint(model.JobToTask, rule=makespan_rule)

model.obj = Objective(expr=model.makespan, sense=minimize)

TransformationFactory('gdp.bigm').apply_to(model)

solver = SolverFactory('glpk')
# solver = SolverFactory('cbc')
solver.solve(model, tee=True)

print("\nFinal Schedule:")
for (job, task) in sorted(model.JobToTask):
    start = model.startTime[job, task].value
    end = model.endTime[job, task].value
    machine = model.taskMachine[job, task]
    print(f"{job}-{task:10s} | Machine: {machine:12s} | Start: {start:.1f} min | End: {end:.1f} min")

print(f"\nTotal Makespan = {model.makespan.value:.1f} minutes or {model.makespan.value / 60:.1f} hours")

print(f"machine utilization:\n")

for machine in machines:
    total_time = sum(model.taskDuration[job, task] for (job, task) in model.JobToTask if model.taskMachine[job, task] == machine)
    utilization = total_time / (max(calendar[machine]) - min(calendar[machine])) * 100
    print(f"{machine}: {utilization:.2f}%")
    print(f"Total time on {machine}: {total_time} minutes\n")

plt.figure(figsize=(10, 6))
colors = {'LaserCutter': 'skyblue', 'CNC_Mill': 'lightgreen', 'PaintStation': 'lightcoral'}
for (job, task) in sorted(model.JobToTask):
    start = model.startTime[job, task].value
    end = model.endTime[job, task].value
    machine = model.taskMachine[job, task]
    plt.barh(job, end - start, left=start, label=task , color=colors[machine])
plt.xlabel('Time (minutes)')
plt.ylabel('Jobs')
plt.title('Gantt Chart of Job Scheduling')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()  
