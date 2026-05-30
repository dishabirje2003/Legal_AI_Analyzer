import sqlite3 
conn = sqlite3.connect(r'backend\\tmp\\job_queue.sqlite3') 
conn.row_factory = sqlite3.Row 
q = '''select id, payload, status, attempts, worker_name, substr(coalesce(last_error,''),1,200) as err from jobs order by id desc limit 10''' 
for row in conn.execute(q): 
    print(dict(row))
