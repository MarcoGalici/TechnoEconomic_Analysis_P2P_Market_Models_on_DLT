[![Contributors][contributors-shield1]][contributors-url1]
[![Contributors][contributors-shield2]][contributors-url2]
[![Contributors][contributors-shield3]][contributors-url3]
[![Contributors][contributors-shield4]][contributors-url4]
[![Contributors][contributors-shield5]][contributors-url5]
[![MIT License][license-shield]][license-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">
    <a href="https://github.com/MTr87/MKT_Comparison/">
        <img src="readme_file/logo-icai.png" alt="Logo" width="500" height="200">
  </a>

<h3 align="center">ENGINITE Platform Comillas</h3>

  <p align="center">
    Techno Economic Analysis of three Double Auction LEM developed on DLT platform.
    <br />
    <a href="https://www.iit.comillas.edu/"><strong>Explore the IIT website »</strong></a>
    <br />
    <br />
    <a href="https://github.com/MTr87/DEV_MRKT_MODELS/issues">Report Bug</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-study">About The Study</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
        <li><a href="#mathematical-formulation">The Congestion Management Problem</a>
      <ul>
        <li><a href="#local-flexibility-market-optimization-model">Local Flexibility Market Optimization Model</a></li>
      </ul>
    </li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Study

<!--[![Product Name Screen Shot][product-screenshot]](https://example.com)-->

<!-- Here's a blank template to get started: To avoid retyping too much info. Do a search and replace with your text editor for the following: `github_username`, `repo_name`, `twitter_handle`, `linkedin_username`, `email_client`, `email`, `project_title`, `project_description`-->
<!-- Link for emoji https://www.webfx.com/tools/emoji-cheat-sheet/ -->

Since the emergence of distributed energy resources, local electricity markets have garnered interest for energy sharing on a community scale through both centralized and distributed models, including innovative distributed platforms. Numerous studies and initiatives have demonstrated that local markets and peer-to-peer transactions can be effective for electricity networks under specific conditions. Amidst the growing exploration of local market models, there is a noticeable gap in quantitative techno-economic analyses comparing different auction mechanisms. This paper aims at filling this gap by representing a comparative analysis of the most commonly implemented double-sided market models for peer-to-peer transactions based on a distributed ledger implementation. The comparison is based on quantitative key performance indicators designed to assess the economic and technical performance of these market models, including technical constraints within the power system through a network constraints management market. According to the selected metrics, the simulation results reveal that no single model outperforms all others. The authors conclude that, under the tested application and assumed conditions, the distributed market using distributed ledger technology faces several challenges that hinder its efficient application to local energy trading.


<!-- Built With -->
### Built With
* [![Python][Python-shield]][Python-url]
* [![Gurobi][Gurobi-shield]][Gurobi-url]

<!-- <p align="right"><a href="#top">🔼 Back to top</a></p> -->

<!-- Mathematical Problems -->
## Mathematical Formulation

<!-- Local flexibility market optimization model -->
### Local flexibility market optimization model
```math
\min_{p^{up}_{i}, p^{down}_{j}, s^{up}_{r}, s^{down}_{r}} \quad { \sum_{i=1}^{FSP_{up}} c^{up}_{i} \cdot p^{up}_{i} + \sum_{j=1}^{FSP_{down}} c^{down}_{j} \cdot p^{down}_{j} + \sum_{r=1}^{R} c^{slack} \cdot (s^{up}_{r} + s^{down}_{r})}
```
```math
\textrm{Subject to:} \quad P^{DSO_{up}}_{r} - \sum_{i=1}^{FSP_{up}} p^{up}_{i} - s^{up}_{r} <= 0 \quad \forall r \in R^{up}
```
```math
\quad P^{DSO_{down}}_{r} - \sum_{j=1}^{FSP_{down}} p^{down}_{j} - s^{down}_{r} <= 0 \quad \forall r \in R^{down}
```
```math
\quad p^{up_{min}}_{i} <= p^{up}_{i} <= p^{up_{max}}_{i} \quad \forall i \in FSP_{up}
```
```math
\quad p^{down_{min}}_{j} <= p^{down}_{j} <= p^{down_{max}}_{j} \quad \forall j \in FSP_{down}
```
```math
\textrm{Where: } \quad {p^{up}_{i}, p^{down}_{j}, s^{up}_{r}, s^{down}_{r} \geq 0}
```
<p align="right"><a href="#top">🔼 Back to top</a></p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
<!-- To create your personalise shield go to: https://shields.io/ -->
[contributors-shield1]: https://img.shields.io/badge/Contributors-Matteo%20Troncia-orange
[contributors-url1]: https://www.iit.comillas.edu/people/mtroncia
[contributors-shield2]: https://img.shields.io/badge/Contributors-Marco%20Galici-green
[contributors-url2]: https://www.iit.comillas.edu/personas/mgalici
[contributors-shield3]: https://img.shields.io/badge/Contributors-Jose_Pablo_Chaves_Avila-skyblue
[contributors-url3]: https://www.iit.comillas.edu/personas/jchaves
[contributors-shield4]: https://img.shields.io/badge/Contributors-MorsyNour-RoyalBlue
[contributors-url4]: https://www.iit.comillas.edu/personas/mmohammed
[contributors-shield5]: https://img.shields.io/badge/Contributors-FabrizioPilo-darkviolet
[contributors-url5]: https://web.unica.it/unica/it/ateneo_s07_ss01.page?contentId=SHD30679
[license-shield]: https://img.shields.io/badge/License-MIT-yellow
<!--https://img.shields.io/badge/License-BSD_3_Clause-yellow-->
[license-url]: https://github.com/MarcoGalici/TechnoEconomic_Analysis_P2P_Market_Models_on_DLT/blob/main/LICENSE
[product-screenshot]: images/screenshot.png
[Python-shield]: https://img.shields.io/badge/Python-py-green
[Python-url]: https://www.python.org/
[Gurobi-shield]: https://img.shields.io/badge/Gurobi-py-red
[Gurobi-url]: https://www.gurobi.com/
