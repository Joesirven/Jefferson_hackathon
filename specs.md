# Jefferson AI  Specs Doc

# What it does:
- Generates sythentic (silicon) representations of voters using ACS (census) data and other publicly available data sources 
- Models voter's support across multiple issues based on the following data that gets ingested:
    - ACS (census) data
    - Polling results & respondents demographic data
    - Other publicly available data sources
    - precinct level election results
    - real-time news articles
    - trending social media    
- I want to model election results and voter response based on the following research papers:
    - https://hai.stanford.edu/assets/files/hai-policy-brief-simulating-human-behavior-with-ai-agents.pdf
    - https://arxiv.org/pdf/2509.05830
    
- ingests precinct level voting data to build model the sytenthic voters
- run simulations of these voters interacting with each other, depending on proximity and shared demographics
- run simulations of these voters consuming news and social media
- start with san francisco and miami-dade county areas
- we should be able to "poll" these voters and analyze their responses.

[maybe] help me decide if these should be done
- fine tune the model based on the results of the polls and simulations, in time
     (so we can run simulations as though they were done in the past and check against the results of the polls)

## v2
- I want to create a dashboard to visualize the results of the simulations and polls
- visualize the synthetic voters in their precincts and their interactions with each other?

## simulations
- spins up environments based on a set geography
- uses the methods defined in the papers provided. 
- 1 synthetic voter per 5 every voter per census tract

## architecture
- spins up vm's for each simulation 
- fastapi for coordinating? 
- LLM uses GLM's coding plan api or GEmini - let's discuss
- hosted on my vps
- docker-compose
- postgresql for logs and storing data
- nginx for serving the dashboard
- do we need queueing system for handling large number of requests?
- react & typescript for frontend
- open to anyting else that I may be missing here. 

# goal
- simulate the upcoming primary elections in san francisco and miami-dade county areas
