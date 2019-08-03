import requests
from bs4 import BeautifulSoup
import json
import re
import sqlite3
from tqdm import tqdm
from datetime import datetime
from itertools import product
from time import sleep

# Getting the Websites
result_url = 'https://makaut.ucanapply.com/smartexam/public/result-details'
get_result_details = 'https://makaut.ucanapply.com/smartexam/public//get-result-details'

# Semester Codes
semcode = ('SM01', 'SM02', 'SM03', 'SM04', 'SM05', 'SM06', 'SM07', 'SM08')

def get_marks_of(rollNo, semester):
    # Handle session cookies appropriately
    s = requests.Session()
    with s.get(result_url) as r:
        while r.status_code != 200:
            r = s.get(result_url)
    
    # Parse CSRF-Token
    soup = BeautifulSoup(r.text, 'html.parser')
    csrf_token = soup.find("meta", {"name":"csrf-token"})['content']

    # Create dict for post request
    form_data = {'_token': csrf_token, 'p1':'', 'ROLLNO':str(rollNo), 'SEMCODE':semcode[semester-1], 'examtype':'result-details', 'all':''}

    # Get Result Data
    with s.post(get_result_details, data=form_data) as r:
        while r.status_code != 200:
            r = s.post(get_result_details, data=form_data)
    
    result_data = json.loads(r.text)['html']

    soup = BeautifulSoup(result_data, 'html.parser')
    result_data = soup.find("div", {"id":"page-wrap"})

    try:
        result_data = result_data.get_text()
    except AttributeError:
        # This result has not yet been published
        return

    fill = lambda x: x[0] if len(x) == 1 else "<Not Found>"

    # Basic Data
    name = fill(re.findall("Name[^a-zA-Z]*([a-zA-Z ]+)", result_data))
    stream = fill(re.findall("B.Tech[^A-Z]*([A-Z]+)", result_data))
    roll_num = fill(re.findall("Roll[^0-9]*([0-9]+)", result_data))
    reg_num, batch = re.findall("Registration[^0-9]*([0-9]+) OF ([0-9-]+)", result_data)[0]

    # Subject Data
    def get_subject_data(result_data):
        re_mp_fl = [ i for i in filter(lambda x: x!='', [i for i in map(lambda x: x.strip(), re.findall("([^\n]+)", result_data))])]
        for i in range(re_mp_fl.index("Subject Code")+6, re_mp_fl.index("Total"),6):
            yield(tuple([re_mp_fl[j] for j in range(i, i+6)]))

    subject_data = get_subject_data(result_data)

    # SGPA YGPA MAR - Prone to errors for odd and even sem
    sgpa_odd, odd_year, sgpa_even, even_year, ygpa = -1, -1, -1, -1, -1
    try:
        sgpa_odd = re.findall("ODD\.*\s*\(.*\)[^0-9.]*([0-9.]+)", result_data)[0]
        odd_year = re.findall("ODD[^0-9]*([0-9])", result_data)[0]
        sgpa_even = re.findall("EVEN\s*\(.*\)[^0-9.]*([0-9.]+)", result_data)[0]
        even_year = re.findall("EVEN[^0-9]*([0-9])", result_data)[0]
        ygpa = re.findall("YGPA[^0-9]*([0-9.]+)", result_data)[0]

    except IndexError:
        pass

    return {
        'name': name,
        'stream': stream,
        'roll': roll_num,
        'reg_num': reg_num,
        'batch': batch,
        'marks_per_subject': subject_data,
        'sgpa_odd': sgpa_odd,
        'odd_year': odd_year,
        'sgpa_even': None if sgpa_even == -1 else sgpa_even,
        'even_year': None if even_year == -1 else even_year,
        'ygpa': None if ygpa == -1 else ygpa
    }

college_code = int(input("? College Code: "))
roll_no_median = int(input("? Roll Number Median that might be available for every stream: "))
extreme_stream_no = int(input("? Maximum Code to try streams: "))

# First Year's year
current_year_last_two = 0
while True:
    current_year_last_two = int(input("? Last Declared First Year's Joining Year: ")[2:])
    if len(str(current_year_last_two)) == 2:
        break
    else:
        print("[!] Oops, try again")

# Stream data
print("\n[#] Collecting Data of Streams available in your college")

streams = []
for stream_num in tqdm(range(1, extreme_stream_no+1)):
    fmt_roll = "%03d%03d%02d%03d"%(college_code, stream_num, current_year_last_two, roll_no_median)
    data = get_marks_of(fmt_roll, 2)
    if data is not None and data['stream'] != '<Not Found>':
        streams.append((data['stream'], stream_num))
print("\n[$] The following streams were found in your college:")
print("[", ", ".join([strm[0] for strm in streams]), "]")

choice = input("\nDo you want to create the database? (Y/N): ")
if choice not in "Yy":
    print("Okay, Goodbye!")
    quit()

# Getting some basic info
sem = ''
while True:
    sem = input("? Last Declared Results were for ODD Semester or for EVEN Semester: ").lower()
    if sem not in ["odd", "even"]:
        print("[X] Please enter properly!")
        continue
    else:
        break
sem = 1 if sem == 'odd' else 0

min_roll, max_roll = 0, 200
while True:
    min_roll = int(input("? Minimum Roll: "))
    max_roll = int(input("? Maximum Roll: "))

    if min_roll>0 and max_roll>0 and max_roll > min_roll and max_roll<250:
        break
    else:
        print("[X] Please enter the maximum and minimum roll numbers properly! Range: (1-250)")
        continue
    
# Which semester numbers to try
start_sem_from = {
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    5: 3,
    6: 3,
    7: 5,
    8: 5
}

# -------------DATABASE------------- #
db_name = input("? Database Name (prexisting): ")
db = sqlite3.connect(db_name)
curr = db.cursor()

# To create table first time
# [BASIC_DATA]
curr.execute('''CREATE TABLE IF NOT EXISTS "basic_data" (
	"roll_no"	NUMERIC,
	"reg_no"	TEXT,
	"name"	TEXT,
	"stream"	TEXT,
	"batch"	TEXT,
	PRIMARY KEY("roll_no")
);''')

# [GPA_DATA]
curr.execute('''CREATE TABLE IF NOT EXISTS "gpa_data" (
	"roll"	NUMERIC,
	"sgpa_1"	TEXT,
	"sgpa_2"	TEXT,
	"sgpa_3"	TEXT,
	"sgpa_4"	TEXT,
	"sgpa_5"	TEXT,
	"sgpa_6"	TEXT,
	"sgpa_7"	TEXT,
	"sgpa_8"	TEXT,
	"ygpa_1"	TEXT,
	"ygpa_2"	TEXT,
	"ygpa_3"	TEXT,
	"ygpa_4"	TEXT,
	"cgpa"	TEXT,
	PRIMARY KEY("roll")
);''')

# [SUBJECT_DATA]
curr.execute('''CREATE TABLE IF NOT EXISTS "subject_data" (
	"id"	INTEGER PRIMARY KEY AUTOINCREMENT,
	"roll"	TEXT,
	"which_sem"	TEXT,
	"paper_code"	TEXT,
	"paper_name"	TEXT,
	"grade"	TEXT,
	"points"	TEXT,
	"credit"	TEXT,
	"credit_points"	TEXT
);''')

for stream_name , stream_num in streams:
    print(f"\n[i] Trying {stream_name} peeps!")
    
    if sem == 1:
        # Odd sem
        sem_max = [i for i in range(7,0,-2)]
    else:
        # Even sem
        sem_max = [i for i in range(8,1,-2)]
    
    # Looping over years
    data_to_try = [i for i in product(range(current_year_last_two-3, current_year_last_two+1), range(min_roll, max_roll+1))]
    for year, rollNo in tqdm(data_to_try):
        complete_roll = int("%03d%03d%02d%03d"%(college_code, stream_num, year, rollNo))
        
        sx = sem_max[year-current_year_last_two-1]
        for sm_no in range(start_sem_from[sx], sx+1):
            data = get_marks_of(complete_roll, sm_no)
            
            if data is not None:
                # Store this data!

                # Update basic data
                res = list(curr.execute("SELECT name FROM basic_data WHERE roll_no = ?", (complete_roll,)))
                if len(res) == 0:
                    # Data already not present
                    curr.execute('''INSERT INTO basic_data(roll_no, reg_no, name, stream, batch) VALUES (?, ?, ?, ?, ?);''', 
                        (data['roll'], data['reg_num'], data['name'], data['stream'], data['batch']))

                # Update GPA
                res = list(curr.execute("SELECT * FROM gpa_data WHERE roll=?", (complete_roll,)))
                if len(res) == 0:
                    # Create and store
                    curr.execute(f'''INSERT INTO gpa_data(roll, sgpa_{data['odd_year']}) VALUES (?,?)''', (data['roll'], data['sgpa_odd']))

                    if data['even_year'] is not None:
                        curr.execute(f'''UPDATE gpa_data SET sgpa_{data['even_year']} = ? WHERE roll = ?''', (data['sgpa_even'], data['roll']))
                    
                    if data['ygpa'] is not None:
                        curr.execute(f'''UPDATE gpa_data SET ygpa_{sm_no // 2} = ? WHERE roll = ?''', (data['ygpa'], data['roll']))

                else:
                    # Update
                    curr.execute(f'''UPDATE gpa_data SET sgpa_{data['odd_year']} = ? WHERE roll = ?''', (data['sgpa_odd'], data['roll']))

                    if data['even_year'] is not None:
                        curr.execute(f'''UPDATE gpa_data SET sgpa_{data['even_year']} = ? WHERE roll = ?''', (data['sgpa_even'], data['roll']))
                    
                    if data['ygpa'] is not None:
                        curr.execute(f'''UPDATE gpa_data SET ygpa_{sm_no // 2} = ? WHERE roll = ?''', (data['ygpa'], data['roll']))

                
                # Update subject data
                for sub_data in data['marks_per_subject']:
                    res = list(curr.execute("SELECT id FROM subject_data WHERE paper_code = ? AND roll = ?", (sub_data[0], complete_roll)))
                    
                    if len(res) == 0:
                        curr.execute('''INSERT INTO subject_data(roll, which_sem, paper_code, paper_name, grade, points, credit, credit_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                            (data['roll'], data['even_year' if sem==0 else 'odd_year'], sub_data[0], sub_data[1], sub_data[2], sub_data[3], sub_data[4], sub_data[5]))

    db.commit()
    sleep(10)

db.commit()
db.close()