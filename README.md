# About
This is a public repository of our project, VetNinja in the Google DevHack 2023 Hackathon.

# Contributors
- Team lead and Python developer: Ng Jing Ying (https://github.com/NGOLDWEEKLY)
- UI/UX Designer: Khoo Zi Yi (https://github.com/ziyikhoo456)
- Business Analyst: So Xin Yuan (https://github.com/Xinyuanso)
- System Designer and Analyst: Teoh Zhen Quan (https://github.com/benteoh0707)

# Installations
To deploy locally, try: uvicorn main:app
1. main.py is the entry point
2. utils/resume_io.py contains main resume screening functions
3. scene/base.py is the context for both Interviewer and Judge
4. in agent/base.py, Interviewer is the data model that handles open-ended assessment, while judge is to assess candidate and interact with recruiters
5. user/base.py contains user authentication module
