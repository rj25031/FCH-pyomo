#Imports 
# import matplotlib
# matplotlib.use('TkAgg')                  # use TkAgg backend for plotting
import matplotlib.pyplot as plt

from pyomo.environ import *
from pyomo.gdp import *

# Machines and their daily working hours (in minutes from midnight)
machines = ['LaserCutter', 'CNC_Mill', 'PaintStation']
calendar = {
    'LaserCutter': list(range(480, 1021, 60)),    #  8:00–17:00
    'CNC_Mill':    list(range(480, 961, 60)),     #  8:00–16:00
    'PaintStation': list(range(540, 1081, 60)),   #  9:00–18:00
}
num_days = 5  # planning horizon in days

# Task definitions: (job_id, task_id, machine, duration_in_hours, predecessor)
tasks = [
    ('Job1', 'Cutting',  'LaserCutter', 3, None),
    ('Job1', 'Milling',  'CNC_Mill',    2, 'Cutting'),
    ('Job1', 'Painting', 'PaintStation',1, 'Milling'),

    ('Job2', 'Cutting',  'LaserCutter', 2, None),
    ('Job2', 'Painting', 'PaintStation',1, 'Cutting'),

    ('Job3', 'Milling',  'CNC_Mill',    4, None),
    ('Job3', 'Painting', 'PaintStation',2, 'Milling'),

    ('Job4', 'Cutting',  'LaserCutter', 5, None),
    ('Job4', 'Milling',  'CNC_Mill',    3, 'Cutting'),
    ('Job4', 'Painting', 'PaintStation',2, 'Milling'),
]

Job_Task = {}
for job_id, task_id, machine, hrs, pred in tasks:
    Job_Task[(job_id, task_id)] = {
        'machine': machine,
        'duration': hrs * 60,   # convert hours → minutes
        'predecessor': pred,
    }

valid_slots_by_task = {}
for (job, task), data in Job_Task.items():
    machine = data['machine']
    duration = data['duration']
    slots = []
    for day in range(num_days):
        offset = 1440 * day
        shift = calendar[machine]
        shift_start = shift[0] + offset
        shift_end = shift[-1] + offset
        for h in shift:
            t0 = h + offset
            if t0 + duration <= shift_end:
                slots.append(t0)
    valid_slots_by_task[(job, task)] = slots

model = ConcreteModel()

# Sets
model.Machines  = Set(initialize=machines)
model.JobToTask = Set(dimen=2, initialize=Job_Task.keys())

# Parameters
model.taskMachine   = Param(
    model.JobToTask,
    initialize={k: v['machine'] for k, v in Job_Task.items()}
)
model.taskDuration  = Param(
    model.JobToTask,
    initialize={k: v['duration'] for k, v in Job_Task.items()}
)
model.taskPredecessor = Param(
    model.JobToTask,
    initialize={k: v['predecessor'] for k, v in Job_Task.items()}
)
model.machineCalendar = Param(
    model.JobToTask,
    initialize=valid_slots_by_task
)
model.taskOnMachine = Param(
    model.Machines,
    initialize={m: [(j, t) for (j, t) in model.JobToTask
                     if model.taskMachine[j, t] == m]
               for m in machines}
)

# Upper bound on makespan (entire horizon in minutes)
UB = 1440 * num_days

# Decision variables
model.startTime    = Var(model.JobToTask, domain=NonNegativeReals, bounds=(0, UB))
model.endTime      = Var(model.JobToTask, domain=NonNegativeReals, bounds=(0, UB))
model.makespan     = Var(domain=NonNegativeReals, bounds=(0, UB))

# start‐slot variables
start_slot_keys = [
    (j, t, s) for (j, t), slots in valid_slots_by_task.items() for s in slots
]
model.StartSlotKeys = Set(dimen=3, initialize=start_slot_keys)
model.startAtSlot   = Var(model.StartSlotKeys, domain=Binary)

#Constraints 
# 1) Task duration linkage
def task_duration_rule(m, j, t):
    return m.endTime[j, t] == m.startTime[j, t] + m.taskDuration[j, t]
model.taskDurationConstraint = Constraint(model.JobToTask, rule=task_duration_rule)

# 2) Precedence constraints
def precedence_rule(m, j, t):
    pred = m.taskPredecessor[j, t]
    if pred is None:
        return Constraint.Skip
    return m.startTime[j, t] >= m.endTime[j, pred]
model.taskPredecessorConstraint = Constraint(model.JobToTask, rule=precedence_rule)

# 3) No‐overlap via GDP disjunctions
overlap_pairs = []
for (j1, t1) in model.JobToTask:
    for (j2, t2) in model.JobToTask:
        if (j1, t1) < (j2, t2) and model.taskMachine[j1, t1] == model.taskMachine[j2, t2]:
            overlap_pairs.append((j1, t1, j2, t2))

def A_before_B_rule(d, j1, t1, j2, t2):
    d.c = Constraint(expr=model.startTime[j2, t2] >= model.endTime[j1, t1])
def B_before_A_rule(d, j1, t1, j2, t2):
    d.c = Constraint(expr=model.startTime[j1, t1] >= model.endTime[j2, t2])

model.A_before_B = Disjunct(overlap_pairs, rule=A_before_B_rule)
model.B_before_A = Disjunct(overlap_pairs, rule=B_before_A_rule)
model.noOverlap  = Disjunction(overlap_pairs,
    rule=lambda m, j1, t1, j2, t2: [m.A_before_B[j1, t1, j2, t2],
                                  m.B_before_A[j1, t1, j2, t2]]
)

# 4) Each task picks exactly one start slot
def one_start_slot_rule(m, j, t):
    return sum(m.startAtSlot[j, t, s]
               for (j0, t0, s) in m.StartSlotKeys
               if j0 == j and t0 == t) == 1
model.oneSlotPerTask = Constraint(model.JobToTask, rule=one_start_slot_rule)

# 5) Link slot choice to startTime
def link_start_time_rule(m, j, t):
    return m.startTime[j, t] == sum(
        s * m.startAtSlot[j, t, s]
        for (j0, t0, s) in m.StartSlotKeys
        if j0 == j and t0 == t
    )
model.linkStartTime = Constraint(model.JobToTask, rule=link_start_time_rule)

# 6) Makespan definition
def makespan_rule(m, j, t):
    return m.makespan >= m.endTime[j, t]
model.makespanConstraint = Constraint(model.JobToTask, rule=makespan_rule)

#Objective 
model.obj = Objective(expr=model.makespan, sense=minimize)

# Solve
TransformationFactory('gdp.bigm').apply_to(model)
solver = SolverFactory('glpk')
solver.solve(model, tee=True)

#Results
print("\nFinal Schedule:")
for j, t in sorted(model.JobToTask):
    st = model.startTime[j, t].value
    et = model.endTime[j, t].value
    mc = model.taskMachine[j, t]
    print(f"{j}-{t:10s} | Machine: {mc:12s} "
          f"| Start: {st:.1f} min | End: {et:.1f} min")

print(f"\nTotal Makespan = {model.makespan.value:.1f} minutes "
      f"({model.makespan.value/60:.1f} hours)\n")

print("Machine Utilization:\n")
for m in machines:
    tot = sum(model.taskDuration[j, t]
              for (j, t) in model.JobToTask if model.taskMachine[j, t] == m)
    util = tot / (max(calendar[m]) - min(calendar[m])) * 100
    print(f"{m}: {util:.2f}% utilization ({tot} minutes)\n")

# Gantt Chart
plt.figure(figsize=(12, 6))
colors = {'LaserCutter': 'red', 'CNC_Mill': 'green', 'PaintStation': 'blue'}
added_labels = set()

for j, t in sorted(model.JobToTask):
    st = model.startTime[j, t].value
    et = model.endTime[j, t].value
    machine = model.taskMachine[j, t]
    label = machine if machine not in added_labels else None
    plt.barh(j, et - st, left=st, color=colors[machine], label=label)
    added_labels.add(machine)

def format_time(t):
    day = int(t) // 1440 + 1
    mins = int(t) % 1440
    hr = mins // 60
    mm = mins % 60
    return f'Day {day}\n{hr:02}:{mm:02}'

makespan = int(model.makespan.value)
xticks = range(0, makespan + 120, 120)
plt.xticks(ticks=xticks, labels=[format_time(t) for t in xticks], rotation=45, fontsize=8)

for d in range(1, makespan // 1440 + 2):
    plt.axvline(x=d * 1440, color='gray', linestyle='--', linewidth=0.7)

plt.xlabel('Time')
plt.ylabel('Jobs')
plt.title('Multi-Day Gantt Chart of Job Scheduling')
plt.legend(title="Machine")
plt.grid(True)
plt.tight_layout()
plt.show()
