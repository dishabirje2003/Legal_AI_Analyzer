import sqlite3 
conn = sqlite3.connect(r'backend\\tmp\\job_queue.sqlite3') 
conn.row_factory = sqlite3.Row 
q1 = '''select id, job_type, status, attempts, available_at, worker_name, substr(coalesce(last_error,''),1,160) as err from jobs order by id desc limit 10''' 
q2 = '''select status, count(*) c from jobs group by status order by status''' 
print('jobs:') 
for row in conn.execute(q1): 
    print(dict(row)) 
print('counts:') 
for row in conn.execute(q2): 
    print(dict(row))
