# To Do

## UI

### Job build card

<!-- * Add role selector to job build card -->
<!-- * Update stat field labels depending on selected role -->
<!-- * Set role based on Etro URL -->
<!-- * Stat fields mobile friendly -->

### FFLogs card

<!-- * Only show jobs within the role -->

### Rotation DPS distribution card

* Mobile friendly graph/table

### Action DPS distributions

* Selector for which actions to display
* x-axis slider with dynamic y-axis scaling
    * better y-axis scaling
    * Partial property callback

## Backend

### Buffs/actions by ID

<!-- * buffs by ID -->
    <!-- * Map ast/radiant finale to damage, append -3, -6, etc to ID -->
    <!-- * Damage buffs for ground effects -->
    <!-- * Ground effect multiplier -->
    <!-- * Move to csv/dataframe so there can be more info like valid start/end -->

    <!-- * Potency be affected by buffs like Meikyo or Requiescat -->
<!-- * actions
    * change action name to buff ID -->

### Data

* 6.4 potency for PLD
    * Figure out timezone of timestamp (VPN action?)
* move leftover dmg_distribution to damage_analysis.py
    * Probably switch mean to 50%
    * I think I can also not have to use numerical integration...
* Start planning potency table management.
