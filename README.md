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
    This project looked at exploring how explainable AI (XAI) techniques could be used to give informative data displays to users of the PassivUK Smart Heat Pump Thermostat system.
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

### FACE Algorithm
TBC

### Forecasting-based Counterfactual Analysis
- [Setpoint](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/setpoint_power_comparison.ipynb)
    - If the user had their setpoint temperature 1 degree C lower, could they save money?
- [ecoHeat](https://github.com/PracticeOrientedAICDT/PassivUK_Project_Spring_2026/blob/dev/explainable-AI/ecoheat_comparison.ipynb)
    - If a user had ecoHeat enabled (instead of disabled) could they save money?
- [Reactive overrides]()
    - What does one override actually cost? If a user had waited instead of overriding the system, how much money would htey have saved?
- [Habitual overrides]()
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

### Exploratory Data Analysis (EDA)
The ```eda``` folder in this repository contains various Jupyter Notebooks exploring various aspects of the Passiv dataset. To run these you will need to copy the data into a folder titled ```data``` within the ```eda``` folder. The notebooks should then be able to run using the virtual environment you made earlier.

### Explainable AI (XAI)
The ```explainable-AI``` folder in this repository contains our implementations using various XAI techniques.

### FACE algorithm
TBC

### Forecasting-based Counterfactual Analysis
A copy of the data must be placed within the ```explainable-AI`` folder in order to run the setpoint and ecoHeat notebooks using the virtual environment. 

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
