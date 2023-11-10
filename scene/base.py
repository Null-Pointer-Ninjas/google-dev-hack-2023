import asyncio
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from agent.base import Interviewer, Judge

class Interview(BaseModel):
    id: UUID
    owner_uid : str
    name: str
    job_desc : list[str]
    interviewer: Interviewer
    speech_content: list[str]
    event_queue: asyncio.Queue[str]
    response_queue: asyncio.Queue [str]

    class Config:
        arbitrary_types_allowed = True 
        
    def __init__(
        self,
        owner_uid,
        id: Optional[UUID] = None,
    ):
        if id is None:
            id = uuid4()

        criteria_task_list = [
            {"criteria":"has strong tech first attitude with a genuine desire to learn"},
            {"criteria":"has good time management skills"}, #implicit
            {"criteria":"loyal and never share confidential information to anyone else"}, #implicit
            {"criteria":"be politeful with our clients (even the clients are low manners)"}, #implicit
         {"criteria":"Strong communication and interpersonal skills"},
         {"criteria": "Able to work independently and as part of a team"},
         {"criteria": "Eager to learn"},
            {"criteria":"loyal and never share confidential information to anyone else"}, #implicit
         {"criteria": "Hardworking"}
]

        job_desc = ["Running online webinars.",
"Conducting interviews with special guests and VIP speakers.",
"Develop plans to reach out to corporate partners",
"Seek sponsorship and partnership for learning programs"
"Leading initiatives to support the growth of girls from childhood to adulthood in the field of Information and Communication Technology (ICT).",
"Work with cross-functional teams with our growth and marketing team to facilitate campaign performance."]

        interviewer = Interviewer(owner_uid,"Event Manager",criteria_task_list, job_desc)
        speech_content = []
        event_queue = asyncio.Queue(maxsize=500)
        response_queue = asyncio.Queue(maxsize=50)

        super().__init__(id=id,
                         owner_uid=owner_uid,
                         name="Interview",
                         job_desc=job_desc,
                         interviewer=interviewer,
                         speech_content=speech_content,
                         event_queue=event_queue,
                         response_queue=response_queue)
    
    async def send_interviewee_input(self, player_input_text: str = None, audio : bytes = None):
        if player_input_text is not None:
            self.speech_content.append(player_input_text)
            await self.event_queue.put("Got Cand Input Event") #Todo: make it a class, instead of str
        else:
            await self.event_queue.put("No Cand Input Event")

    async def start_session(self, audio:bool = False):
        await self.interviewer.run(self.response_queue)
        print("Done init interviewer")
        while True:
            print("running...")
            agent_task = asyncio.create_task(self.interviewer.move(self.response_queue))
            event_msg = await self.event_queue.get()
            if event_msg == "Got Cand Input Event":
                print("Got message")
            else:
                await self.response_queue.put(None) #Stop signal
                return
            text = self.speech_content[-1] 
            agent_task = asyncio.create_task(self.interviewer.plan(text))
            await agent_task

class Assessment(BaseModel):
    id: UUID
    owner_uid : str
    name: str
    judge: Judge
    speech_content: list[str]
    event_queue: asyncio.Queue[str]
    response_queue: asyncio.Queue [str]

    class Config:
        arbitrary_types_allowed = True #To suppress PydanticSchemaGenerationError

    def __init__(
        self,
        owner_uid,
        id: Optional[UUID] = None,
    ):
        if id is None:
            id = uuid4()

        judge = Judge("RNAI")
        speech_content = []
        event_queue = asyncio.Queue(maxsize=500)
        response_queue = asyncio.Queue(maxsize=50)

        super().__init__(id=id,
                         owner_uid=owner_uid,
                         name="Copilot",
                         judge=judge,
                         speech_content=speech_content,
                         event_queue=event_queue,
                         response_queue=response_queue)
    
    async def send_interviewee_input(self, text: str = None):
        player_input_text = text
        print('Player: ', player_input_text)
        if player_input_text is not None:
            self.speech_content.append(player_input_text)
            await self.event_queue.put("Got Input Event") #Todo: make it a class, instead of str
        else:
            await self.event_queue.put("No Input Event")

    async def start_session(self, q:int = 0):
        while True:
            print("running...")
            agent_task = asyncio.create_task(self.judge.move(self.response_queue, q))
            event_msg = await self.event_queue.get()
            if event_msg == "Got Input Event":
                print("Got message")
            else:
                await self.response_queue.put(None) #Stop signal
                return
            text = self.speech_content[-1] 
            agent_task = asyncio.create_task(self.judge.plan(text))
            await agent_task
