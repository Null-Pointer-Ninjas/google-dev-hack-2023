import google.generativeai as palm
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from tabulate import tabulate
import asyncio
import chromadb
from chromadb.api.types import Documents, Embeddings

PALM_API_KEY = "INPUT API KEY HERE"
defaults = {
  'model': 'models/text-bison-001',
  'temperature': 0.2,
  'candidate_count': 1,
  'top_k': 40,
  'top_p': 0.95,
  'max_output_tokens': 1024,
  'stop_sequences': [],
}

AZURE_COGNITIVE_ENDPOINT = "AZURE ENDPOINT"
AZURE_API_KEY = "API KEY"
CONTENT = "content"
PAGE_NUMBER = "page_number"
TYPE = "type"
RAW_CONTENT = "raw_content"
TABLE_CONTENT = "table_content"

credential = AzureKeyCredential(AZURE_API_KEY)
AZURE_DOCUMENT_ANALYSIS_CLIENT = DocumentAnalysisClient(AZURE_COGNITIVE_ENDPOINT, credential)

palm.configure(api_key=PALM_API_KEY)
models = [m for m in palm.list_models() if 'embedText' in m.supported_generation_methods]
model = models[0]

def embed_function(texts: Documents) -> Embeddings:
  # Embed the documents using any supported method
  return  [palm.generate_embeddings(model=model, text=text)['embedding']
           for text in texts]

def azure_analyse_doc(filename:str = None):
       # Open the temporary file in binary read mode and pass it to Azure
    with open(filename, "rb") as f:
        poller = AZURE_DOCUMENT_ANALYSIS_CLIENT.begin_analyze_document("prebuilt-document", document=f)
        doc_info = poller.result().to_dict()
        print(doc_info)
    res = []
    for p in doc_info['pages']:
        dict = {}
        page_content = " ".join([line["content"] for line in p["lines"]])
        dict[CONTENT] = str(page_content)
        dict[PAGE_NUMBER] = str(p["page_number"])
        dict[TYPE] = RAW_CONTENT
        res.append(dict)

    for table in doc_info["tables"]:
        dict = {}
        dict[PAGE_NUMBER] = str(table["bounding_regions"][0]["page_number"])
        col_headers = []
        cells = table["cells"]
        for cell in cells:
            if cell["kind"] == "columnHeader" and cell["column_span"] == 1:
                for _ in range(cell["column_span"]):
                    col_headers.append(cell["content"])

        data_rows = [[] for _ in range(table["row_count"])]
        for cell in cells:
            if cell["kind"] == "content":
                for _ in range(cell["column_span"]):
                    data_rows[cell["row_index"]].append(cell["content"])
        data_rows = [row for row in data_rows if len(row) > 0]

        markdown_table = tabulate(data_rows, headers=col_headers, tablefmt="pipe")
        dict[CONTENT] = markdown_table
        dict[TYPE] = TABLE_CONTENT
        res.append(dict)
    return res

def get_or_create_pdf_collection(collection_name : str, filepath: str, filename : str):
    client = chromadb.PersistentClient(path=filepath)
    print("filepath, ", filepath)
    client.heartbeat()
    try:
        collection = client.get_collection(collection_name, embedding_function=embed_function)
        print("Collection exist.")
        return collection
    except:
        print("Collection not found, creating new one...")
        collection = client.create_collection(collection_name, embedding_function=embed_function)
        res = azure_analyse_doc(filename=filepath+filename)
        id = 1
        for dict in res:
            content = dict.get(CONTENT, '')
            page_number = dict.get(PAGE_NUMBER, '')
            type_of_content = dict.get(TYPE, '')

            content_metadata = {   
                PAGE_NUMBER: page_number,
                TYPE: type_of_content
            }
            print("adding: ", content)
            print("adding metadata: ", content_metadata)
            collection.add(
                documents=[content],
                metadatas=[content_metadata],
                ids=[str(id)]
        )
            id += 1
        return collection



def get_or_create_report_collection(filepath: str):
    client = chromadb.PersistentClient(path=filepath)
    client.heartbeat()
    try:
        collection = client.get_collection(f"sessions_collection", embedding_function=embed_function)
        print("Collection exist.")
        return collection
    except:
        print("Collection not found, creating new one...")
        try:
            collection = client.create_collection(f"sessions_collection", embedding_function=embed_function)
        except Exception as ex:
            print(ex)
        return collection

def get_relevant_passage(query, db):
  passage = db.query(query_texts=[query], n_results=1)['documents']
  print(passage)
  if(len(passage) > 0 and len(passage[0]) >0 ):
      return passage[0][0]
  else:
      return "No relevant info"

def make_prompt(query, relevant_passage):
  escaped = relevant_passage.replace("'", "").replace('"', "").replace("\n", " ")
  prompt = ("""You are a helpful and informative bot that justify whether a job applicant possess the skill from the reference passage included below. \
  Be sure to respond in a complete sentence, being comprehensive. \
  If the passage is irrelevant to the skill, you may ignore it. \
  SKILL: '{query}'
  PASSAGE: '{relevant_passage}'
    REVIEW:
  """).format(query=query, relevant_passage=escaped)

  return prompt
def make_info_prompt(query, relevant_passage):
  escaped = relevant_passage.replace("'", "").replace('"', "").replace("\n", " ")
  prompt = ("""You are a helpful and informative bot that can extract the relevant information based on the passage, if there is more than one answer, use a list. \
  If the passage is irrelevant to the information, you should say 'FALSE'. \
  INFORMATION: 'full name'
  PASSAGE: 'BACHELOR OF COMPUTER SCIENCE (HONS) UNIVERSITI TUNKU ABDUL RAHMAN John Malaysia'
  VALUE: John
  INFORMATION: 'experience'
  PASSAGE: 'RESEARCH EXPERIENCE Doctoral Researcher Department of English, University of Illinois at Urbana-Champaign 20XX-20XX · Conducted primary source research at numerous archives, examining publication history through multiple sources. · Examined the literature of William Faulkner, Thomas Wolfe, and Tennessee Williams, exploring their publication records, construction of literary identity, and relationship with modernism. Research Assistant Department of English, University of Illinois at Urbana-Champaign 20XX · Assistant to Professor Robert Warren, conducting primary and secondary source research. · Organized for the "New Directions in the Study of Southern Literature: An Interdisciplinary Conference." PUBLICATIONS Associate Editor of North Carolina Slave Narratives. John Jacob Franz, general editor. Forthcoming from University of Illinois Press, 20xx. Johnson, JM, Lolie, T., and Green, R. "Lost on the Farm: Popular Beliefs" Somebody Journal, Special Issue, Reflections on the Americas. Vol. 6. Accepted and forthcoming. Green, R. "Fugitives/Agrarians" in A Companion to Twentieth-Century American Poetry. Rutgers Press., 20xx. Davis, D.A. and Green, R. "Will N. Harben," "Etheridge Knight," and "James Wilcox" in Southern Writers: A Biographical Dictionary. Louisiana State University Press, 20xx. CONFERENCE PRESENTATIONS "Artistic Colloquialism," Illinois Graduate College Seminar, speaker and organizer. Urbana, IL, 20xx. "Transitional Bible Belt," US Divergence Symposium, Duke University, NC, February 20xx. "The Ministry of Rev. Thomas H. Jones," South Atlantic Modern Language Association. Atlanta, GA, May 20xx. "Shackles and Stripes: The Cinematic Representation of the Southern Chain Gain." American Literature Association. Cambridge, Massachusetts, November 20xx. "Body Place of Sprits in the South," Queen Mary College, University of London, April 6-8, 20xx. HONORS AND AWARDS Jacob K. Javitz Fellowship, U.S. Department of Education 20xx-present Graduate College Dissertation Completion Award, University of Illinois 20XX Campus Teaching Award based on student evaluations, University of Illinois 20XX-20XX Doctoral Fellowship, Illinois Program for Research in the Humanities, University of Illinois 20XX-20XX Summer Research Grant, Center for Summer Studies, City, ST 20XX Graduate College Conference Travel Grant, University of Illinois 20xX & 20XX Most Outstanding Butler Woman, Butler University, Indianapolis, IN 20XX Academic Scholarship, Butler University, Indianapolis, IN 20XX-20XX Rachel Green, page 2 of 3 4 grad.illinois.edu/CareerDevelopment'
  VALUE: ["Doctoral Researcher": ["Department of English, University of Illinois at Urbana-Champaign", "20XX-20XX", "Conducted primary source research at numerous archives, examining publication history through multiple sources.", "Examined the literature of William Faulkner, Thomas Wolfe, and Tennessee Williams, exploring their publication records, construction of literary identity, and relationship with modernism."],"Research Assistant":["Department of English, University of Illinois at Urbana-Champaign","20XX","Assistant to Professor Robert Warren, conducting primary and secondary source research.","Organized for the New Directions in the Study of Southern Literature: An Interdisciplinary Conference."]]
  INFORMATION: '{query}'
  PASSAGE: '{relevant_passage}'
    VALUE:
  """).format(query=query, relevant_passage=escaped)

  return prompt

class ResumeReader:
    def __init__(self, username:str, filepath:str= None, filename: str=None):
      if filepath is None:
         print("Failed to create resume reader.")
         return
      self.db = get_or_create_pdf_collection(f"{username}_collection",f"files/{username}/",filename)
      text_models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
      self.model = text_models[0]
      print("success")
      
    def store_assessment(self, infos : list[dict]):
        for i in infos:
            content_metadata = {   
                TYPE: "raw_content",
                PAGE_NUMBER: 1,
               "criteria": i["criteria"]
            }
            content = f"When the candidate is asked, '{i['question']}', they answered, {i['answer']}"
            self.db.add(
                documents=[content],
               metadatas=[content_metadata],
                ids=[str(self.db.count()+1)]
        )
    async def palm_gen_text(self, prompt):
        response = await asyncio.to_thread( palm.generate_text, prompt=prompt, model=self.model, candidate_count=3, temperature=0.2, max_output_tokens=1000)
        if(len(response.candidates)==0):
            answer="not relevant"
        else:
            answer=response.candidates[0]['output']
        return answer

    async def extract_info(self, infos):
        print("answering")
        feedback = []
        tasks = []
        for i in infos:
            print(i)
            passage = get_relevant_passage(i, self.db)
            print(passage)
        
            prompt = make_info_prompt(i, passage)
            agent_task = asyncio.create_task(self.palm_gen_text(prompt))
            tasks.append(agent_task)
        for i in tasks:
            ans = await i
            feedback.append(ans)
            print(ans)
        return feedback

    def match_skill(self, skills):
        feedback = []
        for i in skills:
            passage = get_relevant_passage(i, self.db)
            prompt = make_prompt(i, passage)
            print(prompt)
            answer = palm.generate_text(prompt=prompt, model=self.model, candidate_count=3, temperature=0.2, max_output_tokens=1000)
            print(answer)
            if(len(answer.candidates) == 0):
                feedback.append("not relevant")  
            else:           
                feedback.append(answer.candidates[0]['output'])
        return feedback
    def summarise(self, criteria_list):
        skills = self.match_skill(criteria_list)
        return ' '.join(skills)

    def answer(self, query, temperature=0.5):
        print("answering")
        passage = get_relevant_passage(query, self.db)
        prompt = make_prompt(query, passage)
        answer = palm.generate_text(prompt=prompt, model=self.model, candidate_count=3, temperature=temperature, max_output_tokens=1000)
        return answer.candidates[0]['output']

def make_report_prompt(query, relevant_passage):
  escaped = relevant_passage.replace("'", "").replace('"', "").replace("\n", " ")
  prompt = ("""You are a helpful and informative bot that summarise the interview transcript. \
  Be sure to respond in a complete sentence, being comprehensive. \
  If the passage is irrelevant to the criteria, you may ignore it. \
  PASSAGE: 'In the interview session, the interviewer presented a series of scenarios to the interviewee, each dealing with different work-related situations. The first scenario involved working on a campaign with a cross-functional team, comprising individuals from various departments with diverse working styles. The interviewer inquired about the interviewee's approach to ensuring the success of the campaign and effective collaboration within the team. In response to this first scenario, the interviewee replied, "I don't know" in just 31 seconds. The second scenario involved collaborating with the growth team and the need to share confidential information with the marketing team. The marketing team requested the information to be shared during a meeting with angry customers. The interviewer sought the interviewee's guidance on handling this sensitive situation. The interviewee's response to the second scenario was, once again, "I don't know," and the answer was provided in 32 seconds. The final scenario involved the task of interviewing a famous and demanding chef who was a VIP speaker at a major food event. The chef was known for being particular about their food and interviews. The interviewer inquired about the interviewee's strategy for ensuring a smooth interview and making the chef happy with the results. In a brief response lasting 14 seconds, the interviewee humorously suggested, "Bribe him" as a way to handle the situation. These scenarios and the interviewee's responses reflect various challenges and situations one might encounter in a professional setting.'
  SUMMARY: In this interview session, the interviewer asked the interviewee a series of questions related to various work scenarios. The interviewee's responses were very brief and indicated a lack of knowledge or understanding of how to handle the situations effectively. The interviewee responded with "I don't know" to the first two questions, suggesting a lack of preparedness or expertise. However, in response to the third question about handling a demanding chef, the interviewee made an inappropriate suggestion to "bribe him," which is not a suitable or ethical approach to handling such a situation. Overall, the interviewee's responses raise concerns about their suitability for the positions discussed in the questions.
  PASSAGE: '{relevant_passage}'
    SUMMARY:
  """).format(query=query, relevant_passage=escaped)

  return prompt

def genCriteria(title, desc, req):
    
    prompt = ("""You are a job screening criteria generator. Generate the criteria based on job description and requirement. \
  JOB_TITLE: 'Event Manager'
  JOB_DESCRIPTION: You will have a significant impact on the planning and execution of several offline and online events in this capacity. Your duties will include everything from careful planning to making sure everything runs smoothly on the day of the event. The event manager will be the key to the success of every event, working with different teams and outside partners to make each one unforgettable.
  JOB_REQUIREMENT: Academic qualification in Marketing, Management, Business, Public Relations, Advertising, Multimedia, Psychology, or equivalent. Passion. Willing to learn. Experienced in Project Management.
    CRITERIA: academic qualified; event management; passion; eager to learn; multitasking; problem solving; teamwork
  JOB_TITLE: '{title}'
  JOB_DESCRIPTION: {desc}
  JOB_REQUIREMENT: {req}
    CRITERIA:
  """).format(title=title, desc=desc, req=req)
    text_models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]

    answer = palm.generate_text(prompt=prompt, model=text_models[0], candidate_count=3, temperature=0.2, max_output_tokens=1000)
    if (len(answer.candidates) == 0):
        return "ethical; teamwork; diligent; eager to learn" #Default
    else:
        return answer.candidates[0]['output']

class CandidateReader:
   def __init__(self, filepath:str= None):
      if filepath is None:
         print("Failed to create resume reader.")
         return
      self.db = get_or_create_report_collection(filepath)
      print(self.db.get())
      text_models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
      self.model = text_models[0]
      print("success")
   def store_candidate(self, username, cand_meta, candidate_summ):
       content_metadata = {   
                TYPE: "raw_content",
                PAGE_NUMBER: 1,
                "name" : username,
                "brief" : cand_meta
            }
       print(content_metadata, candidate_summ)
       self.db.add(
                documents=[f"This is {username}."+candidate_summ],
                metadatas=[content_metadata],
                ids=[str(self.db.count()+1)]
        )
   def answer(self, query, temperature=0.5):
    print("answering")
    passage = get_relevant_passage(query, self.db)
    #TODO: make this better
    prompt = make_report_prompt(query, passage)
    answer = palm.generate_text(prompt=prompt, model=self.model, candidate_count=3, temperature=temperature, max_output_tokens=1000)
    return answer.candidates[0]['output']
   
   def grade(self, criteria, q_id=None, regrade_rule: str = None,temperature=0.5):
    print("answering")
    passage = self.db.get(ids=[q_id])['documents'][0]
    print(passage)
    escaped = passage.replace("'", "").replace('"', "").replace("\n", " ")
    if regrade_rule is not None:
        note = f'Please pay attention on this advice when evaluating, "{regrade_rule}".'
    else:
        note = ""
    xml = "<Criteria>"
    #return xml
    for i in criteria:
        print("i")
        prompt = ("""You are a helpful and informative bot that will evaluate this candidate resume and open-ended assessment record. \
  Be sure to respond in XML format. \
  If the passage is irrelevant to the criteria, you may ignore it. \
    {note}
  PASSAGE: 'This is johndoe.Yes, the candidate possesses the skill of being able to work independently and as part of a team. They were able to provide a comprehensive answer to the question, which showed that they have the ability to work independently and as part of a team. No, the candidate does not possess the skill of being able to meet deadlines and work under pressure. Yes, John has a strong tech first attitude with a genuine desire to learn. He is an undergraduate student who is enthusiastic about computer science knowledge since he was young. He has participated in many competitions and won several awards. He is also working as a software developer intern, where he implemented an algorithm to enhance video conferencing quality. it is not possible to tell Yes, the candidate has good time management skills. They were able to quickly come up with a comprehensive plan for managing their time and resources to ensure the success of the initiative. no, the candidate does not possess the skill of being loyal and never sharing confidential information to anyone else No, the candidate does not possess strong communication and interpersonal skills.'
  CRITERIA: academic qualification
  EVALUATION: <Criterion><Title>academic qualification</Title><Score>3</Score><Description>The candidate is academically qualified for the job title.</Description><Resume>The candidate's academic qualification is briefly mentioned as being an undergraduate student enthusiastic about computer science since a young age. However, the resume does not provide specific details about their academic performance, GPA, or any relevant coursework. It would be beneficial to have more information to evaluate the candidate's academic qualification properly. Additional information such as the university, major, and any notable achievements or projects would be helpful.</Resume><Assessment>not available</Assessment></Criterion>
  PASSAGE: '{relevant_passage}'
  CRITERIA: {criteria}
  EVALUATION:
  """).format(note=note,criteria=i, relevant_passage=escaped)

        answer = palm.generate_text(prompt=prompt, model=self.model, candidate_count=3, temperature=temperature, max_output_tokens=1000)
        xml+=answer.candidates[0]['output']
    xml+= "</Criteria>"
    return xml

