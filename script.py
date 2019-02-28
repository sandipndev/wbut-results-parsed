import requests
from bs4 import BeautifulSoup
import json

# Range of Roll Number - User Input
start_roll = int(input("Starting Roll Number: "))
end_roll = int(input("Ending Roll Number: "))

# Semester - User Input
sem = int(input("Which Semester[1-8]: "))

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
        for x in result_data.find_all("strong"):
            foo = x.get_text()
            if 'Name' in foo:
                name = foo[7:]
            elif 'SGPA' in foo:
                sgpa = foo[(foo.find(':')+1):]
                break
        return (name, sgpa)
    
    except AttributeError:
        return ('<Not Found>')

for roll in roll_tuple:
    print(get_marks_of(roll, sem))
