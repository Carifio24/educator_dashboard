import requests
from requests import Session
import os
import json
import numpy as np
from urllib.parse import urljoin
from dotenv import load_dotenv
from pathlib import Path  # python3 only

API_URL = "https://api.cosmicds.cfa.harvard.edu"
HUBBLE_ROUTE_PATH = "hubbles_law"

from .State import State, StateList
    
class QueryCosmicDSApi():
    
    url_head = API_URL
    querystring = {"":""}
    payload = ""
    headers = {"authority": "api.cosmicds.cfa.harvard.edu"}
    
    def __init__(self, story = HUBBLE_ROUTE_PATH, class_id = None):
        self.class_id = class_id
        self.story = story
        dotenv_path = Path(__file__).resolve().parent.parent.parent / '.env'
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path)
        self._request_session = self.request_session()
        pass
    
    
    def get_env(self):
        api_key = os.getenv('CDS_API_KEY')
        assert os.environ is None
        if api_key is None:
            print("PLEASE SET CDS_API_KEY ENVIRONMENT VARIABLE")
    
        return api_key
    
    def in_dev_mode(self):
        dev_mode = os.getenv('CDS_DEV_MODE')
        api_key = self.get_env()
        return (api_key is not None) and (dev_mode is not None)
    
    def request_session(self):
        """
        Returns a request session object that has the 
        relevant authorization praameters to interface
        with the CosmicDS API server (provided environment 
        variables are set correctly)
        """
        session = requests.Session()        
        assert self.get_env() is not None
        session.headers.update({'Authorization': self.get_env()})
        return session
    
    @staticmethod
    def l2d(list_of_dicts):
        "list of dicts to dict of lists"
        if isinstance(list_of_dicts, dict):
            return list_of_dicts
        if isinstance(list_of_dicts, list) and len(list_of_dicts) == 0:
            return {}
        keys = list_of_dicts[0].keys()
        dict_of_lists = {k: np.asarray([o[k] for o in list_of_dicts]) for k in keys}
        return dict_of_lists
    
    def get(self, url):
        response = self._request_session.get(url)
        return response
        
        
    def get_roster(self, class_id = None, story = None):
        """
        Returns the Roster for a given class_id and story
        returns the student information and the story state
        """
        class_id = self.class_id or class_id
        story = self.story or story
        
        endpoint = f'roster-info/{class_id}'
        if (story is not None) and (story != ''):
            endpoint += f'/{story}'
        url = urljoin(self.url_head, endpoint)
        self.roster_url = url
        req = self.get(url)
        return req.json()
    
    def get_student_data(self, student_id, story = None):
        """
        returns student ID and measurements
        """
        story = self.story or story

        endpoint = f'{story}/measurements/{student_id}'
        url = urljoin(self.url_head, endpoint)
        self.student_url = url
        req = self.get(url)
        try:
            return req.json()
        except json.JSONDecodeError:
            print(req.text)
            return None
    
    def get_class_data(self, class_id = None, student_ids = None, story = None):
        class_id = self.class_id or class_id
        story = self.story or story

        ## Can also use stage-3-data enpoint to get the data
        ## this is a little fast since it runs on the serve
        ## but I feel like /all-data is more robust
        roster = self.get_roster(class_id, story = story)
        student_id = [student['student_id'] for student in roster]
        if len(student_id) == 0:
            return None
        
        # endpoint = f"{story}/stage-3-data/{student_id}/{class_id}"
        # url = '/'.join([self.url_head, endpoint])
        # self.class_summary_url = url
        # req = self.get(url)
        # try:
        #     return self.l2d(req.json()['measurements'])
        # except json.JSONDecodeError:
        #     print(req.text)
        #     return None
        
        if (class_id is None) and (student_ids is None):
            return None
        
        if student_ids is None:
            filter_fun = lambda m: m['class_id'] == class_id
            measurements = [m for m in self.get_all_data(story = story, transpose = False)['measurements'] if filter_fun(m)]
            # check that there are measurements for every student_id   
        else:
            if isinstance(student_ids, int):
                student_ids = [student_ids]
            measurements = [self.get_student_data(student_id)['measurements'] for student_id in student_ids]
            
        if len(measurements) == len(roster):
            return self.l2d(measurements)
        else:
            missing_students = [student['student_id'] for student in roster if student['student_id'] not in [m['student_id'] for m in measurements]]
            print(f"Missing data for students: {missing_students}")
            new_measurements = []
            for student_id in missing_students:
                new_measurements +=  self.get_student_data(student_id)['measurements']
                # self.get_student_data(student_id)['measurements'] for student_id in missing_students]
            new_measurements = [m for m in new_measurements if len(m) > 0]
            # add class_id to new measurements
            for m in new_measurements:
                m['class_id'] = class_id
                m['student'] = {'flagged': True}
            # print(new_measurements)
            return self.l2d(measurements + new_measurements)

    def get_student_summary(self, class_id = None):
        summary = self.get_all_data(transpose = False)
        if class_id is None:
            return self.l2d(summary['studentData'])
        else:
            filt = lambda m: m['class_id'] == class_id
            return self.l2d([m for m in  summary['studentData'] if filt(m)])
        
    
    def get_all_data(self, story = None, transpose = True):
        story = self.story or story
        
        url = f"{self.url_head}/{story}/all-data"
        all_data = self.get(url).json()
        
        if transpose:
            return {
                'measurements': self.l2d(all_data['measurements']),
                'studentData': self.l2d(all_data['studentData']),
                'classData': self.l2d(all_data['classData'])
                }
        else:
            return all_data
    
    def example_galaxy(self, class_id = None, student_id = None, story = None):
        
        class_id = class_id or self.class_id
        story = story or self.story
        
        endpoint = 'hubbles_law/sample-measurements'
        url = urljoin(self.url_head, endpoint)
        self.example_galaxy_url = url
        req = self.get(url)
        return req.json()
    

    def get_question(self, question_tag):
        endpoint = f'/question/{question_tag}'
        url = urljoin(self.url_head, endpoint)
        self.question_url = url
        print(url)
        req = self.get(url)
        if req.status_code == 404:
            print(f"Question {question_tag} not found")
            return None
        return req.json()
    
    def get_questions(self, story = None):
        story = self.story or story
        endpoint = f'questions/{story}'
        url = urljoin(self.url_head, endpoint)
        self.questions_url = url
        print(url)
        req = self.get(url)
        if req.status_code == 200:
            return {q['tag']:q for q in req.json()['questions']}
        
    def get_class_for_teacher(self,teacher_key = None):
        endpoint = f"/dashboard-group-classes/{teacher_key}"
        url = urljoin(self.url_head, endpoint)
        self.teacher_classes_url = url 
        print(url)
        req = self.get(url)
        if req.status_code == 404:
            print(f"Teacher code {teacher_key} not found")
            return { 'class_ids' : [] }
        else:
            return req.json()
            
        
        
