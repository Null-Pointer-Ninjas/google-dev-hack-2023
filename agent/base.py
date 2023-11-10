from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
import json
import time
import math
import asyncio
import random
import google.generativeai as palm
from utils.resume_io import *


PALM_API_KEY = "API KEY HERE"
defaults = {
  'model': 'models/text-bison-001',
  'temperature': 0.2,
  'candidate_count': 1,
  'top_k': 40,
  'top_p': 0.95,
  'max_output_tokens': 1024,
  'stop_sequences': [],
#  'safety_settings': [{"category":"HARM_CATEGORY_DEROGATORY","threshold":1},{"category":"HARM_CATEGORY_TOXICITY","threshold":1},{"category":"HARM_CATEGORY_VIOLENCE","threshold":2},{"category":"HARM_CATEGORY_SEXUAL","threshold":2},{"category":"HARM_CATEGORY_MEDICAL","threshold":2},{"category":"HARM_CATEGORY_DANGEROUS","threshold":2}],
}

defaults_chat = {
  'model': 'models/chat-bison-001',
  'temperature': 0.2,
  'candidate_count': 1,
  'top_k': 40,
  'top_p': 0.95,
#  'safety_settings': [{"category":"HARM_CATEGORY_DEROGATORY","threshold":1},{"category":"HARM_CATEGORY_TOXICITY","threshold":1},{"category":"HARM_CATEGORY_VIOLENCE","threshold":2},{"category":"HARM_CATEGORY_SEXUAL","threshold":2},{"category":"HARM_CATEGORY_MEDICAL","threshold":2},{"category":"HARM_CATEGORY_DANGEROUS","threshold":2}],
}
palm.configure(api_key=PALM_API_KEY)

class Interviewer(BaseModel):
    id: UUID
    owner_uid : str
    name: str
    memory : list[str] #TODO: create memory class
    criteria_task_list: list[dict]
    job_desc:list[str]
    cur_criteria_task: int
    cur_plan: list[str]
    transcript: list[dict]
    report: list[str]
    wait_start: float

    class Config:
        arbitrary_types_allowed = True #To suppress PydanticSchemaGenerationError

    def __init__(self, 
                 owner_uid:str,
                 name: str,
                 criteria_task_list: list[str] = [],
                 job_desc: list[str] = [],
                id: Optional[UUID] = None,):
        
        if id is None:
            id = uuid4()

        memory = []
        cur_criteria_task= 0
        cur_plan = []
        report = []
        random.shuffle(criteria_task_list)
        transcript = []
        wait_start = 0
        super().__init__(id=id, 
                         owner_uid=owner_uid,
                         name=name, 
                         memory=memory,
                         criteria_task_list=criteria_task_list,
                         job_desc=job_desc,
                         cur_criteria_task=cur_criteria_task,
                         cur_plan=cur_plan,
                         report=report,
                         transcript=transcript,
                         wait_start=wait_start
                         )
        print(f"[INFO] Interviewer #{name} initialisation complete.")
        
    def gen_task_list(self, criteria_task_list:list[str], job_desc: str=None):
        prev_criteria_list = []
        for i in criteria_task_list:
            if i is None:
                continue
            prompt = f"""You are recruiter AI hiring an {self.name}. Using one sentence, describe how the respective skill can be assessed in terms of the relevant job description.
Skill: Problem Solving
Job Description: Leading initiatives to support the growth of girls from childhood to adulthood in the field of Information and Communication Technology (ICT).
Sentence: A good problem solver shall effectively resolve any critical situations.
Skill: {i}
Job Description: {job_desc}
Sentence:"""
        
            plannerResponse = palm.generate_text(
            **defaults,
            prompt=prompt
            )
            prev_criteria_list.append(plannerResponse.result)
        print("criteria left:", prev_criteria_list)
        secrets = ["Johor", "Friendly", "Online", "tech-savvy", "finance", "industry", "multiracial", "save", "Kuala Lumpur", "Penang", "food", "book"]
        prompt = f"""You are a creative job description generator. Based on the secret text, generate a similar job description in 1 sentence.
Secret: Malaysia
Job Description: Prepare pre-recorded lessons and learning materials
New Job Description: Prepare pre-recorded videos and learning materials which are related to Malaysia history
Secret: {random.choice(secrets)}
Job Description: {job_desc}
New Job Description:"""
        
        jobResponse = palm.generate_text(
            **defaults,
            prompt=prompt
            )
        job_desc = jobResponse.result

        print(job_desc)
        prompt = f"""You are recruiter AI hiring an {self.name}. Based on the Criteria and the Job Description, design a scenario-based question where the candidate need to answer about how they can handle the scenario. Your scenario must be illustrated in a specific and realistic manner.
Criteria: A good event manager should be always politeful to customers. A good event manager should behave professionally.
Job Description: conducting interviews with special guests and VIP speakers
Question: You are tasked with conducting an interview with a highly-respected VIP speaker at a major event. As you are preparing to start the interview, the VIP speaker arrives, but they seem visibly flustered and stressed. They are also running a bit late. The audience is eagerly waiting, and there's a tight schedule to maintain. How would you handle this situation to ensure the interview starts smoothly and the VIP speaker feels respected and valued while maintaining professionalism and politeness?
Criteria: {'. '.join(prev_criteria_list)}
Job Description: {job_desc}
Question:"""
        plannerResponse = palm.generate_text(
            **defaults,
            prompt=prompt
            )
        return plannerResponse.result
    
    async def move(self, response_queue : asyncio.Queue):
        print(self.cur_criteria_task, " ,", len(self.criteria_task_list))
        
        if self.cur_criteria_task  > len(self.criteria_task_list)+ 3:
            print(self.transcript)
            resumeReader = ResumeReader(username=self.owner_uid, filepath=f"files/{self.owner_uid}/", filename="abc.pdf")
            resumeReader.store_assessment(self.transcript )
            skills = []
            for i in self.criteria_task_list:
                skills.append(i['criteria'])
            candidate_summ = resumeReader.summarise(skills)
            candReader = CandidateReader(filepath=f"files/")
            prompt = f"""You are a skills extractor, write out all the skills based on the passage
Passage: The candidate is able to work as a team. The candidate has strong desire to learn. The candidate knows how to use C++.
Skills: teamwork, passionate, C++
Passage: {candidate_summ}
Skills:"""
            sunnResponse = palm.generate_text(
            **defaults,
            prompt=prompt
            )
            cand_meta = sunnResponse.result
            candReader.store_candidate(self.owner_uid, cand_meta, candidate_summ)
            json_obj = json.dumps(self.transcript, indent=4)
            with open(f"files/{self.owner_uid}/transcript-{str(round(time.time()))}.json", 'w') as f:
                f.write(json_obj)
            await response_queue.put("ENDED")
            return
        else:
            print(self.memory)
            replyQuestion = self.memory[-1]
        judge_avatar = {'ended': False}
        judge_avatar['message'] = replyQuestion
        self.wait_start = time.time()
        await response_queue.put(judge_avatar)
        await response_queue.put(None) #Stop Signal
        print(f"Placed {self.id} to queue", self.id)

    async def plan(self, input_text: str):
        input_text = input_text.replace("\n", ' ').replace(":", ".")
        for i in range(len(self.transcript)):
            self.transcript[i]["answer"] = f"(answered within {str(math.floor(time.time() - self.wait_start))}s) "+input_text
        self.cur_criteria_task += 3
        job_desc = random.choice(self.job_desc)
        if len(self.criteria_task_list) > 3+self.cur_criteria_task:
            self.memory = [await asyncio.to_thread(self.gen_task_list, self.criteria_task_list[self.cur_criteria_task:3+self.cur_criteria_task], job_desc=job_desc)]
            for i in self.criteria_task_list[self.cur_criteria_task:3+self.cur_criteria_task]:
                self.transcript.append({"criteria":i['criteria'],"question": self.memory[-1]})
        elif self.cur_criteria_task  > len(self.criteria_task_list)+ 3:
            self.memory = ["Completed"]
        else:
            self.memory = [await asyncio.to_thread(self.gen_task_list, self.criteria_task_list[-3:], job_desc=job_desc)]
            for i in self.criteria_task_list[-3:]:
                self.transcript.append({"criteria":i['criteria'],"question": self.memory[-1]})

    async def run(self, response_queue : asyncio.Queue,):
        job_desc = random.choice(self.job_desc)
        if len(self.criteria_task_list) > 3+self.cur_criteria_task:
            self.memory = [await asyncio.to_thread(self.gen_task_list, self.criteria_task_list[self.cur_criteria_task:3+self.cur_criteria_task], job_desc=job_desc)]
            for i in self.criteria_task_list[self.cur_criteria_task:3+self.cur_criteria_task]:
                self.transcript.append({"criteria":i['criteria'],"question": self.memory[-1]})
        else:
            self.memory = [await asyncio.to_thread(self.gen_task_list, self.criteria_task_list, job_desc=job_desc)]
            for i in self.criteria_task_list:
                self.transcript.append({"criteria":i['criteria'],"question": self.memory[-1]})

        await response_queue.put({"progress":0.5})
        await response_queue.put({"progress":1.0})
        print("Generated task list, ", self.criteria_task_list)
        return
    

class Judge(BaseModel):
    id: UUID
    name: str
    memory : list[str] #TODO: create memory class
    messages: list[str]
    correction_status: str
    criteria_task_list: list[str]
    cur_criteria_task: int
    cur_question: str
    transcript: list[dict]
    report: list[str]
    wait_start: float

    class Config:
        arbitrary_types_allowed = True #To suppress PydanticSchemaGenerationError

    def __init__(self, 
                 name: str,
                id: Optional[UUID] = None,):
        
        if id is None:
            id = uuid4()

        criteria_task_list = [
           "academic qualified",
           "eager to learn",
           "loyal and never share confidential information to anyone else", #implicit
           "able to handle stress",
           "teamwork",
           "communication skills"
        ] 
        memory = []
        correction_status= 'NONE'
        messages = []
        cur_criteria_task= 0
        cur_question = "No question"
        report = []
        transcript = []
        wait_start = 0
        super().__init__(id=id, 
                         name=name, 
                         cur_question=cur_question,
                         memory=memory,
                         messages=messages,
                         correction_status=correction_status,
                         criteria_task_list=criteria_task_list,
                         cur_criteria_task=cur_criteria_task,
                         report=report,
                         transcript=transcript,
                         wait_start=wait_start
                         )
        print(f"[INFO] Interviewer #{name} initialisation complete.")
        
    def view_candidates(self, criteria_task_list):
        self.memory = [" I am reviewing candidate resume. "]
        resumeReader = CandidateReader(filepath=f"files/")
        print(resumeReader.db.get())

        for i in range(1,20):
            answer= resumeReader.grade(criteria_task_list,str(i))
            self.memory.append(answer)
            print(answer)
        # temporary
        
        print(self.memory)
        self.memory.append("Done reviewing resume.")

    async def move(self, response_queue : asyncio.Queue, q:int):
        if self.correction_status == 'PENDING':
            resumeReader = CandidateReader(filepath=f"files/")
            answer= resumeReader.grade(self.criteria_task_list,str(q), self.cur_question)
            replyQuestion = {'candidate_brief': answer}
        if self.cur_question == "No question" and q is not None and q > 0:
            resumeReader = CandidateReader(filepath=f"files/")
            answer= resumeReader.grade(self.criteria_task_list,str(q))
            replyQuestion = {'candidate_brief': answer}
        elif self.cur_question == "No question":
            replyQuestion = "Hi Mr Farhan. How can I help you today?"
        elif  "Correct Your Marking" in self.cur_question:
            replyQuestion = "Sure, I'll follow your instructions. Please provide an example of why I am wrong, I will try to re-grade every candidate based on your rule."
            self.correction_status = 'PENDING'
            self.messages.append(f"""
There are some mistakes when you are grading the open-ended assessment, can you please re-grade it?
""")
            self.messages.append(replyQuestion)
        else:
            palm.configure(api_key=PALM_API_KEY)
            print(self.memory)
            context = f"You are the HR helper of me, Mr. Farhan. You need to respond me accordingly in a short and concise manner, please refer to your memory here: <p>{' '.join(self.memory)}</p> when answering my questions."
            examples = [
  [
    "Hi, do you think Joseph is suitable for an event manager role?",
    "Based on the open-ended assessment result, I do not think Joseph is suitable for an event manager role.\n\nIn the first question, Joseph was asked how he would handle a situation where he is interviewing a VIP speaker who is opinionated and outspoken. Joseph did not provide a clear answer, and instead said \"I don't know.\" This suggests that he may not have the skills and experience necessary to handle difficult situations.\n\nIn the second question, Joseph was asked how he would handle a situation where one of his team members comes to him with confidential information. Joseph again did not provide a clear answer, and instead said \"I don't know.\" This suggests that he may not be able to handle sensitive information in a confidential manner.\n\nOverall, the interview transcript suggests that Joseph may not have the skills and experience necessary to be an event manager. He did not provide clear answers to the questions, and his answers suggested that he may not be able to handle difficult situations or confidential information."
  ]
]
            if len(self.messages) > 5:
                del self.messages[0]
            if "Summarise" in self.cur_question:
                ques= "Give a short statistics about all the candidates, like how many candidates got how many personal values, if I were to move forward for the next qualification round, which candidates should be preferred. Write in 1 paragraph without using tables."
            else:
                ques=self.cur_question
            self.messages.append(f"""
{ques}
""")
            response = palm.chat(
  **defaults_chat,
  context=context,
  examples=examples,
  messages=self.messages
)
            print("==================")
            print('LLM Result 1: ', response.last)
            replyQuestion = response.last
            self.messages.append(replyQuestion)
        self.transcript.append({"Interviewer": replyQuestion})
        aids = {"RNAI":0, "Lila": 1, "Ali": 2}
        judge_avatar = {'id':aids[self.name],'voice_id':''}
        judge_avatar['message'] = replyQuestion
        self.wait_start = time.time()
        await response_queue.put(judge_avatar)
        await response_queue.put(None) #Stop Signal
        print(f"Placed {self.id} to queue", self.id)

    async def plan(self, input_text: str):
        input_text = input_text.replace("\n", ' ').replace(":", ".")
        self.cur_question = input_text
        prompt = f"""You are a helpful bot specialising in searching information. Based on the question, generate a list of short text that will be used for searching.
Question: Who is the most capable person that can work as a team to solve complex problems?
List: teamwork, problem solving
Question: {input_text}
List:"""
        plannerResponse = palm.generate_text(
            **defaults,
            prompt=prompt
            )
        query = plannerResponse.result
        resumeReader = CandidateReader(filepath="files/")
        if "Summarise" in input_text:
            if len(self.memory) > 0:
                self.memory.clear()
            self.view_candidates(self.criteria_task_list)
        else:
            answer= resumeReader.answer(query)
            self.memory.append(answer)
            if len(self.memory) > 1:
                del self.memory[0]
