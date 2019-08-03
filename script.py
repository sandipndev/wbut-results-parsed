import requests
from bs4 import BeautifulSoup
import json
import re

# Range of Roll Number - User Input
start_roll = int(input("Starting Roll Number: "))
end_roll = int(input("Ending Roll Number: "))

# Semester - User Input
sem = int(input("Which Semester[1-8]: "))

# Verbosity
verbose = int(input("Verbosity Level (1 for just data, 2 for detailed data): "))

# Roll Number Tuple
roll_tuple = tuple(range(start_roll, end_roll+1))

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
    

    # Basic Data
    name = re.findall("Name[^a-zA-Z]*([a-zA-Z ]+)", result_data)[0]
    stream = re.findall("B.Tech[^A-Z]*([A-Z]+)", result_data)[0]
    roll_num = re.findall("Roll[^0-9]*([0-9]+)", result_data)[0]
    reg_num, batch = re.findall("Registration[^0-9]*([0-9]+) OF ([0-9-]+)", result_data)[0]

    # Subject Data
    def get_subject_data(result_data):
        re_mp_fl = [ i for i in filter(lambda x: x!='', [i for i in map(lambda x: x.strip(), re.findall("([^\n]+)", result_data))])]
        for i in range(re_mp_fl.index("Subject Code")+6, re_mp_fl.index("Total"),6):
            yield(tuple([re_mp_fl[j] for j in range(i, i+6)]))

    subject_data = get_subject_data(result_data)

    # SGPA YGPA MAR - Prone to errors for odd and even sem
    sgpa_odd, odd_year, sgpa_even, even_year, ygpa, cgpa = -1, -1, -1, -1, -1, -1
    try:
        sgpa_odd = re.findall("ODD\.*\s*\(.*\)[^0-9.]*([0-9.]+)", result_data)[0]
        odd_year = re.findall("ODD[^0-9]*([0-9])", result_data)[0]
        sgpa_even = re.findall("EVEN\s*\(.*\)[^0-9.]*([0-9.]+)", result_data)[0]
        even_year = re.findall("EVEN[^0-9]*([0-9])", result_data)[0]
        ygpa = re.findall("YGPA[^0-9]*([0-9.]+)", result_data)[0]
        cgpa = re.findall("DGPA[^EVEN]*EVEN\s*\(.*\)[^0-9.]*[0-9.]+\s*([0-9.]+)[^YGPA]*YGPA", result_data)[0]

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
        'ygpa': None if ygpa == -1 else ygpa,
        'cgpa': None if cgpa == -1 else cgpa
    }

def print_marks_properly(roll, sem):
    data = get_marks_of(roll, sem)
    if data != "<TBD>":
        for key, value in data.items():
            if key == 'marks_per_subject':
                print(key,"->")
                for x in value:
                    print(x)
            else:
                print(key, "->", value)

if verbose == 1:
    # Disply most recent
    for roll in roll_tuple:
        data = get_marks_of(roll, sem)
        try:
            print(f"({data['name']}, {data['sgpa_odd' if sem%2!=0 else 'sgpa_even']})")
        except:
            pass
elif verbose == 2:
    for roll in roll_tuple:
        print_marks_properly(roll, sem)
else:
    print("[!] Verbosity Level Wrong!")
