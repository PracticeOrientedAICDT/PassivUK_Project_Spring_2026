<!-- PROJECT SHIELDS -->
<!--
*** uses markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]


<h3 align="center">PassivUK Project Spring 2026</h3>

  <p align="center">
    This project looked at exploring how explainable AI (XAI) techniques could be used to give informative data displays to users of the PassivUK Smart Heat Pump Thermostat system. To better understand the code in this repository please request a copy of the final report from one of the team members listed below.
    <br />
    <a href="https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026"><strong>Explore the code »</strong></a>
    <br />
    <a href="https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/wiki"><strong>Explore the wiki »</strong></a>
    <br />
    <br />
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

This project was part of the Practice Projects module in TB2 2026, for the Practice-Oriented AI CDT at the University of Bristol. 

There are two strands to our interpretability/explainability investigations:
1. FACE Counterfactual XAI Algorithm
Adaption of the FACE (Feasible and Actionable Counterfactual Explanations) framework proposed by [Poyiadzi et al.](https://dl.acm.org/doi/10.1145/3375627.3375850).

2. Forecasting-based Counterfactual Analysis
Using the ecoHeat API to forecast the impact of altering user behaviour across a period of time.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started
Repository files and their purpose - links to each part of the repository associated with the various investigations are provided below:

- [Event reformatter](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/event_reformat.py)
    - Reformats the event data schedules to match the format required by the ecoHeat API.

- [Survey analysis](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/eda/survey_analysis.ipynb)
    - Code for producing the graphs for our survey analysis

### Exploratory Data Analysis (EDA)
- Temperature data:
    - [thermostat_data_eda](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/eda/thermostat_data_eda.ipynb) - plots temperature, hot water, and tariff data by week or day across the whole dataset
    - [thermostat_data_specific_range](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/eda/thermostat_eda_specific_range.ipynb) - plots temperature, hot water, and tariff data for a specific time range
- Event data:
    - [events_EDA](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/eda/events_EDA.ipynb) - explores the event data
    - [user_behaviour](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/eda/user_behaviour.ipynb) - explores the user behaviour present within the event data
- Both:
    - [eda_tempoverride](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/eda/eda_tempoverride.ipynb) - combines the overrides from the event data with the temperature profiles

### FACE Algorithm
- [FACE model code](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/face_cf.py) and [example implementation](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/face_example.ipynb).
    - Finds feasible and actionable changes a user could make to prevent the need for overrides. 

### Forecasting-based Counterfactual Analysis
- [Setpoint](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/setpoint_power_comparison.ipynb)
    - If the user had their setpoint temperature 1 degree C lower, could they save money?
- [ecoHeat](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/ecoheat_comparison.ipynb)
    - If a user had ecoHeat enabled (instead of disabled) could they save money?
- [Reactive overrides](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/baseline_override_comparison_real.py)
    - What does one override actually cost? If a user had waited instead of overriding the system, how much money would htey have saved?
- [Habitual overrides](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/baseline_override_comparison_real.py)
    - If users with habitual overrides changed their schedule, how much money could they save?

## Prerequisites
This repository requires python version 3.14.0.


## Installation

1. Clone and enter the repo
   ```sh
   git clone https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026.git

   cd PassivUK_Project_Spring_2026
   ```
2. To run the code in this repository, set up a virtual environment with python version 3.14.0. Install the required packages using
    ```sh
    pip install -r requirements.txt
    ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- USAGE EXAMPLES -->
## Usage
### Data
The data used for the project can be accessed via our Teams repository [here](https://uob.sharepoint.com/:f:/r/teams/grp-grp-passiv/Shared%20Documents/General/Passiv%20Data/PSTData5?csf=1&web=1&e=QsJqUr) - for access rights please contact the team members listed below.

The data can be reformatted using ```event_reformat.py``` to produce schedules of the format matching those required by the Passiv API. Copies of the reformatted data are also stored within the Teams repository [here](https://uob.sharepoint.com/:f:/r/teams/grp-grp-passiv/Shared%20Documents/General/PSTData5_reformat_v3?csf=1&web=1&e=qebCYb).


User survey results can be found on the Team repository [here](https://uob.sharepoint.com/:x:/r/teams/grp-grp-passiv/Shared%20Documents/General/Passiv%20Data/survey_responses.xlsx?d=w53873a624ceb4870a0b8843c89722582&csf=1&web=1&e=8J1Nmz), this data is required to run the [survey_analysis](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/eda/survey_analysis.ipynb) Notebook to produce the figures for our report.


### EDA
The ```eda``` folder in this repository contains various Jupyter Notebooks/python codes exploring various aspects of the Passiv dataset. To run these you will need to copy the data into a folder titled ```data``` within the ```eda``` folder. The notebooks/code should then be able to run using the virtual environment you made earlier.

### Explainable AI (XAI)
The ```explainable-AI``` folder in this repository contains our implementations using various XAI techniques.

#### FACE algorithm
The code for the FACE algorithm is contained in [```face_cf.py```](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/face_cf.py). An example implementation of this algorithm can be viewed and run in the [```face_example.ipynb```](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/face_example.ipynb) notebook.

#### Forecasting-based Counterfactual Analysis
A copy of the data must be placed within the ```explainable-AI``` folder in order to run the [setpoint](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/setpoint_power_comparison.ipynb) and [ecoHeat](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/ecoheat_comparison.ipynb) notebooks using the virtual environment. 

The code in [```baseline_override_comparison_real.py```](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/baseline_override_comparison_real.py) should be used to reproduce the override counterfactual analysis.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- LICENSE -->
<!-- ## License

Distributed under the project_license. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p> -->


<!-- CONTACT -->
## Contact

### Team Members:

- Chakaya Nyamvula: nyamvula.chakaya@bristol.ac.uk
- Isobel Higgins: isobel.higgins@bristol.ac.uk
- Priya Kharbanda: mm25873@bristol.ac.uk
- Abby Morris: abby.morris@bristol.ac.uk


<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Thanks is given to Edwin, Rosie and William from PassivUK for mentoring this project and acting as our industry stakeholders. Thank you also to David, Jack, Kenton, Telmo and Miquel for their support in class.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/PracticeOrientedAICDT/PassivUK_Project_Spring_2026.svg?style=for-the-badge
[contributors-url]: https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/PracticeOrientedAICDT/PassivUK_Project_Spring_2026.svg?style=for-the-badge
[forks-url]: https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/network/members
[stars-shield]: https://img.shields.io/github/stars/PracticeOrientedAICDT/PassivUK_Project_Spring_2026.svg?style=for-the-badge
[stars-url]: https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/stargazers
[issues-shield]: https://img.shields.io/github/issues/PracticeOrientedAICDT/PassivUK_Project_Spring_2026.svg?style=for-the-badge
[issues-url]: https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/issues
[license-shield]: https://img.shields.io/github/license/PracticeOrientedAICDT/PassivUK_Project_Spring_2026.svg?style=for-the-badge
[license-url]: https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/master/LICENSE.txt
