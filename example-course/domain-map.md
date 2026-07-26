topic: Espresso — extraction theory for people who own a machine
terminal-task: diagnose a bad shot from taste and timing alone, and name
  the single variable to change next
research: no
timezone: America/Los_Angeles
sessions: 12

<!-- A deliberately tiny course (12 sessions, 7 concepts) whose only job
     is to be a complete, valid, readable instance of the elenchus
     format. A real course runs 20-50 sessions with ~0.75x concepts. -->

### extraction-yield
def: the share of the coffee bean's soluble mass that ends up dissolved in the cup
prereqs: []
verify: quiz
threshold: yes
misconceptions:
  M1: treats "stronger" as identical to "more extracted"
  M2: assumes longer brewing always extracts more

### strength-vs-extraction
def: strength is dissolved solids per unit water; extraction is what fraction you pulled out — independent axes
prereqs: [extraction-yield]
verify: quiz
threshold: yes
misconceptions:
  M1: collapses the two axes into one "strong/weak" scale
  M2: thinks adding water changes how extracted the coffee is

### grind-size
def: the dominant lever on flow resistance, and therefore on contact time and yield
prereqs: [extraction-yield]
verify: quiz
threshold: no
misconceptions:
  M1: treats grind as a taste dial rather than a resistance dial

### sour-vs-bitter
def: sour signals under-extraction, bitter signals over-extraction — the primary diagnostic axis
prereqs: [extraction-yield]
verify: quiz
threshold: yes
misconceptions:
  M1: reads sourness as "too strong" and dilutes it
  M2: assumes bitterness always means the beans are burnt

### brew-ratio
def: the mass of liquid out per mass of dry coffee in, the other half of the strength equation
prereqs: [strength-vs-extraction]
verify: quiz
threshold: no
misconceptions:
  M1: confuses ratio with shot duration

### channeling
def: water finding a low-resistance path through the puck, over-extracting one route while under-extracting the rest
prereqs: [grind-size]
verify: quiz
threshold: no
misconceptions:
  M1: blames the grinder for what is actually a distribution problem

### dialing-in
def: the judgment loop — change one variable, taste, attribute the change, repeat
prereqs: [sour-vs-bitter, grind-size, brew-ratio]
verify: use
threshold: yes
misconceptions:
  M1: changes two variables at once, then cannot attribute the result
  M2: chases a recipe from the internet instead of the taste in the cup

## Sources
- unit-01-a — extraction fundamentals primer (distilled)
- unit-02-a — diagnostic taste chart (distilled)

## Errata
<!-- append only; machine-applicable edge ops merged by every run -->
