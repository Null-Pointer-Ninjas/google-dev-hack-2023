#To deploy locally, try
#uvicorn main:app

# 1. main.py is the entry point
# 2. utils/resume_io.py contains main resume screening functions
# 3. scene/base.py is the context for both Interviewer and Judge
# 4. Interviewer is the data model that handles open-ended assessment, while judge is to assess candidate and interact with recruiters
# 5. user/base.py contains user authentication module