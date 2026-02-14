# What are Architecture Decision Records (ADRs)?

Taken from https://adr.github.io/madr/, Architecture
Decision Records are markdown based records of major
architectural decisions that have occurrend in a project.
By including these docs formally within the source code,
you can gain insight into the major decision drivers and
see some potential alternatives that were considered but
ultimately rejected.

# How to use

A more thorough walkthrough of using the docs can be found at the website above, but generally speaking the steps are:

* Make a copy of the madr_template.md file
* Rename copy using the format
    `<sequential adr ####>-<title of decision>.md`
* Use as much or as little of the template as needed to
    accurate record the driving reasons why a change
    was explored, what potential options were considered,
    and what the ultimate decision outcome was
* Check in your ADR and request review for further comments
    on proposal
    