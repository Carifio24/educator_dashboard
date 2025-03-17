import warnings
warnings.filterwarnings('ignore') # ignore warnings
from .markers import markers
from numpy import nan, isnan
from typing import Dict, List, Optional, Union, Any, cast

from .old_types import (
    StageState, 
    MCScore as ProcessedMCScore, 
    ClassInfo, 
    StudentInfo, 
    OldStudentStoryState, 
    StateInterface
)

from ..logging import logger

# 
class State:
    markers = markers
    
    def __init__(self, story_state: OldStudentStoryState) -> None:
        # list story keys
        self.story_state = story_state
        self.name = story_state.get('name','') # string
        self.title = story_state.get('title','') # string
        self.stages: Dict[str, StageState] = {k:v.get('state',{}) for k,v in story_state['stages'].items()} #  dict_keys(['0', '1', '2', '3', '4', '5', '6'])
        class_room_keys = ['id', 'code', 'name', 'active', 'created', 'updated', 'educator_id', 'asynchronous']
        self.classroom: ClassInfo = cast(ClassInfo, story_state.get('classroom',{k:None for k in class_room_keys}))# dict_keys(['id', 'code', 'name', 'active', 'created', 'updated', 'educator_id', 'asynchronous'])
        self.responses: Dict[str, Dict[str, str]] = story_state.get('responses',{})
        self.mc_scoring: Dict[str, Dict[str, ProcessedMCScore]] = story_state.get('mc_scoring',{}) # dict_keys(['1', '3', '4', '5', '6'])
        self.stage_index = story_state.get('stage_index',nan) # int
        self.total_score = story_state.get('total_score',nan) #int
        self.student_user: Dict[str, Any] = story_state.get('student_user',{}) # dict_keys(['id', 'ip', 'age', 'lat', 'lon', 'seed', 'dummy', 'email', 'gender', 'visits', 'password', 'username', 'verified', 'last_visit', 'institution', 'team_member', 'last_visit_ip', 'profile_created', 'verification_code'])
        self.teacher_user = story_state.get('teacher_user',None) # None
        self.max_stage_index = story_state.get('max_stage_index',0) # int
        self.has_best_fit_galaxy = story_state.get('has_best_fit_galaxy',False) # bool
        self.stage_map: Dict[int, str] = {int(k): k for k in self.stages.keys() if k.isdigit()}
        for k, v in self.stages.items():
            if isinstance(v, dict) and 'index' in v:
                self.stage_map[v['index']] = k
    
    def get_possible_score(self) -> int:
        possible_score = 0
        for key, value in self.mc_scoring.items():
            for v in value.values():
                possible_score += 10
        return possible_score
    
    def stage_score(self, stage) -> tuple[int, int]:
        score = 0
        possible_score = 0
        if str(stage) not in self.mc_scoring:
            return score, possible_score
        
        for key, value in self.mc_scoring[str(stage)].items():
            if value is None:
                score += 0
            else:
                v = value.get('score',0)
                if v is None:
                    score += 0
                else:
                    score += v
            
            possible_score += 10
        return score, possible_score
    
    def stage_name_to_index(self, name: str) -> Optional[int]:
        # 
        d = {v:k for k, v in self.stage_map.items()}
        return d.get(name, None)
    
    @property
    def how_far(self) -> Dict[str, Union[str, float]]:
        stage_index = self.max_stage_index
        if isnan(stage_index):
            return {'string': 'No stage index', 'value':0.0}
        stage_markers = self.markers.get(str(stage_index),None)
        
        frac = self.stage_fraction_completed(stage_index)
        # are we in slideshow stage
        if stage_markers is None:
            string_fmt =  "In Stage {} slideshow".format(stage_index)
        else:
            string_fmt = f"{frac:.0%} through Stage {stage_index}"
            
        return {'string': string_fmt, 'value':frac}
    
    def stage_fraction_completed(self, stage) -> float:
        if stage is None:
            return 1.0
        markers = self.markers.get(str(stage), None)
        
        if markers is None:
            return 1.0
            
        stage_str = str(stage)
        if stage_str not in self.stages:
            return 0.0
            
        current_stage_marker = self.stages[stage_str].get('marker', None)
        if current_stage_marker is None:
            return 0.0
            
        total = len(markers)
        if current_stage_marker not in markers:
            return nan
        current = markers.index(current_stage_marker) + 1
        frac = float(current) / float(total)
        return frac
    
    def total_fraction_completed(self) -> Dict[str, Union[float, int]]:
        total = []
        current = []
        for key, stage in self.stages.items():
            markers = self.markers.get(key,None)
            if markers is not None:
                total.append(len(markers))
                if self.stage_index == int(key):
                    if self.current_marker in markers:
                        val = markers.index(self.current_marker) + 1
                    else:
                        val = nan
                elif self.max_stage_index > int(key):
                    # if true, then stage key is complete
                    val = len(markers)
                elif self.stage_index < int(key):
                    # if false, then stage key is not complete
                    val = 0
                else:
                    val = 0
                current.append(val)
        # logger.debug(total, current)
        if nan in current:
            frac = nan
        else:
            frac = int(100 * float(sum(current)) / float(sum(total)))
        return {'percent':frac, 'total':sum(total), 'current':sum(current)}
    
    @property
    def possible_score(self) -> int:
        return self.get_possible_score()
    
    @property
    def score(self) -> float:
        return self.total_score / self.possible_score
    
    @property
    def story_score(self) -> int:
        total = 0
        for key, stage in self.stages.items():
            score, possible = self.stage_score(key)
            total += score
        return total
    
    @property
    def current_marker(self) -> str:
        stage_data = self.stages.get(str(self.stage_index),{})
        return stage_data.get('marker','none')
    
    @property
    def max_marker(self) -> str:
        stage_data = self.stages.get(str(self.max_stage_index),{})
        return stage_data.get('marker','none')
    
    @property
    def percent_completion(self) -> float:
        return self.total_fraction_completed()['percent']
