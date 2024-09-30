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
    <a href="https://euniversal.eu/"><strong>Explore the Official website »</strong></a>
    <br />
    <br />
    <a href="https://github.com/github_username/repo_name">View Demo</a>
    ·
    <a href="https://github.com/MTr87/DEV_MRKT_MODELS/issues">Report Bug</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
        <li><a href="#mathematical-formulation">The Optimisation Problems</a>
      <ul>
        <li><a href="#local-flexibility-market-optimization-model">Local Flexibility Market Optimization Model</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

<!--[![Product Name Screen Shot][product-screenshot]](https://example.com)-->

<!-- Here's a blank template to get started: To avoid retyping too much info. Do a search and replace with your text editor for the following: `github_username`, `repo_name`, `twitter_handle`, `linkedin_username`, `email_client`, `email`, `project_title`, `project_description`-->
<!-- Link for emoji https://www.webfx.com/tools/emoji-cheat-sheet/ -->

The EUniversal project, funded by the European Union, has developed a universal approach on the use of flexibility by Distribution System Operators (DSO) and their interaction with the new flexibility markets, enabled through the development of the concept of the Universal Market Enabling Interface (UMEI) – a unique approach to foster interoperability across Europe.

The UMEI represents an innovative, agnostic, adaptable, modular and evolutionary approach that will be the basis for the development of new innovative services, market solutions and, above all, implementing the real mechanisms for active consumer, prosumer, and energy communities participation in the energy transition.


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
\min_{\delta p, \delta q, \alpha, \beta} \quad { \sum_{t=1}^{NT} [\sum_{f=1}^{NF} (C^{U_{P}}_{f,t} \cdot \Delta p^{U}_{f,t} + C^{D_{P}}_{f,t} \cdot \Delta p^{D}_{f,t}) + (C^{U_{Q}}_{f,t} \cdot \Delta q^{U}_{f,t} + C^{D_{Q}}_{f,t} \cdot \Delta q^{D}_{f,t}) + \sum_{i=1}^{N_{PB}} C^{\alpha} \cdot \left| \alpha_{i,t} \right| + \sum_{j=1}^{N_{CL}} C^{\beta} \cdot \left| \beta_{j,t} \right|] }
```
```math
\textrm{Subject to:} \quad \Delta S^{CL}_{j,t} <= \sum_{f=1}^{NF} [K^{P}_{j,f} \cdot (\Delta p^{U}_{f,t} - \Delta p^{D}_{f,t}) + K^{Q}_{j,f} \cdot (\Delta q^{U}_{f,t} - \Delta q^{D}_{f,t})] \quad \forall j \in N_{CL} \quad \forall t \in NT
```
```math
\quad v^{B}_{i,t} - V^{A}_{i,t} = \sum_{f=1}^{NF} [H^{P}_{i,f} \cdot (\Delta p^{U}_{f,t} - \Delta p^{D}_{f,t}) + H^{Q}_{i,f} \cdot (\Delta q^{U}_{f,t} - \Delta q^{D}_{f,t})] \quad \forall i \in N_{PB} \quad \forall t \in NT
```
```math
\quad V^{max} <= v^{B}_{i,t} <= V^{min} \quad \forall i \in N_{PB} \quad \forall t \in NT
```
```math
\quad 0 <= \Delta p^{U}_{f,t} <= P^{U_{max}} \quad \forall f \in NF \quad \forall t \in NT
```
```math
\quad 0 <= \Delta p^{D}_{f,t} <= P^{D_{max}} \quad \forall f \in NF \quad \forall t \in NT
```
```math
\quad 0 <= \Delta q^{U}_{f,t} <= Q^{U_{max}} \quad \forall f \in NF \quad \forall t \in NT
```
```math
\quad 0 <= \Delta q^{D}_{f,t} <= Q^{D_{max}} \quad \forall f \in NF \quad \forall t \in NT
```
```math
\textrm{Where: } \quad {P^d_{i,t}, Q^d_{i,t}, SoC_{w,t}, P_{z,t}, Q_{z,t}, P^{cut}_{z,t}, P^{rb}_{z,t}, s^{pVoLV,d}_{i,t}, s^{qVoLV,d}_{i,t} \geq 0}
```
```math
\quad {P^g_{i,t}, Q^g_{i,t}, P_{f,t}, s^{pVoLV,g}_{i,t}, s^{qVoLV,g}_{i,t} \leq 0}
```
```math
\quad {- \infty \leq P_{w,t}, Q_{w,t}, Q_{f,t}, \Delta P_{i,t}, \Delta Q_{i,t}, P^{bus}_{i,t}, Q^{bus}_{i,t} \leq \infty}
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
[contributors-shield4]: https://img.shields.io/badge/Contributors-Orlando%20Mauricio-RoyalBlue
[contributors-url4]: https://www.iit.comillas.edu/personas/mmohammed
[contributors-shield5]: https://img.shields.io/badge/Contributors-FabrizioPilo-darkviolet
[contributors-url5]: https://web.unica.it/unica/it/ateneo_s07_ss01.page?contentId=SHD30679
[license-shield]: https://img.shields.io/badge/License-BSD_3_Clause-yellow
<!--https://img.shields.io/badge/License-MIT-yellow-->
[license-url]: https://img.shields.io/badge/License-MIT-yellow
[product-screenshot]: images/screenshot.png
[Python-shield]: https://img.shields.io/badge/Python-py-green
[Python-url]: https://www.python.org/
[Gurobi-shield]: https://img.shields.io/badge/Gurobi-py-red
[Gurobi-url]: https://www.gurobi.com/
