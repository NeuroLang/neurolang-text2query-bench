texts: null 328, cogat 1138, bench 27, phrase 94; studies 64920
median score: null 0.641, in-domain 0.672; range of medians 0.572-0.751

| statistic | AUC fit | AUC fit typed | null p95 | null p99 | check FPR@p99 | check keep@p99 (cogat/bench/phrase) | check FPR@p95 | check keep@p95 |
|---|---|---|---|---|---|---|---|---|
| max | 0.886 | 0.950 | 0.7821 | 0.7885 | 0.030 | 0.410 (0.38/0.64/0.68) | 0.030 | 0.508 |
| top20 | 0.905 | 0.953 | 0.7618 | 0.7718 | 0.018 | 0.457 (0.43/0.64/0.77) | 0.030 | 0.584 |
| median | 0.818 | 0.837 | 0.6832 | 0.6956 | 0.012 | 0.192 (0.18/0.36/0.32) | 0.012 | 0.348 |
| top20-median | 0.798 | 0.950 | 0.0968 | 0.1018 | 0.018 | 0.283 (0.24/0.57/0.70) | 0.030 | 0.410 |
| zmax_mad | 0.471 | 0.697 | 5.5986 | 6.1870 | 0.012 | 0.017 (0.01/0.07/0.04) | 0.079 | 0.062 |
| zmax_sd | 0.443 | 0.664 | 5.5196 | 6.1154 | 0.006 | 0.010 (0.01/0.00/0.02) | 0.067 | 0.038 |
| ztop20_mad | 0.544 | 0.783 | 4.4507 | 4.6632 | 0.018 | 0.095 (0.07/0.21/0.34) | 0.073 | 0.163 |
| ztop20_sd | 0.519 | 0.767 | 4.3909 | 4.5634 | 0.018 | 0.062 (0.04/0.14/0.26) | 0.055 | 0.087 |
| n(zmad>=3) | 0.637 | 0.812 | 225.7000 | 337.4800 | 0.018 | 0.203 (0.19/0.29/0.38) | 0.098 | 0.381 |
| n(zsd>=3) | 0.638 | 0.815 | 195.4000 | 273.1100 | 0.012 | 0.165 (0.15/0.29/0.30) | 0.085 | 0.327 |
| n(zmad>=4) | 0.545 | 0.796 | 22.0000 | 35.4800 | 0.030 | 0.157 (0.14/0.29/0.36) | 0.055 | 0.221 |
| n(zsd>=4) | 0.517 | 0.776 | 17.0000 | 30.5900 | 0.024 | 0.083 (0.06/0.21/0.30) | 0.067 | 0.173 |
| n(zmad>=5) | 0.504 | 0.666 | 2.0000 | 4.7400 | 0.006 | 0.070 (0.05/0.21/0.28) | 0.024 | 0.098 |
| n(zsd>=5) | 0.470 | 0.601 | 2.0000 | 4.0000 | 0.006 | 0.029 (0.02/0.14/0.13) | 0.024 | 0.054 |
| n(zmad>=6) | 0.509 | 0.575 | 0.0000 | 1.0000 | 0.006 | 0.014 (0.01/0.00/0.06) | 0.030 | 0.022 |
| n(zsd>=6) | 0.493 | 0.508 | 0.0000 | 1.0000 | 0.006 | 0.002 (0.00/0.00/0.02) | 0.018 | 0.017 |
| old floor: top5%>=0.75 | 0.873 | 0.936 | 61.0000 | 240.8900 | 0.012 | 0.405 (0.38/0.57/0.68) | 0.024 | 0.562 |

Short phrases, bench topics and the null's highest (gate at the fit null's 99th percentile):

| kind | text | max | top20 | median | zmax_mad | ztop20_mad | ztop20_sd | n(zmad>=5) | old floor: top5%>=0.75 |
|---|---|---|---|---|---|---|---|---|---|
| bench | tapping fingers in sequence | 0.773 | 0.757 | 0.652 | 4.723- | 4.096- | 4.127- | 0- | 18- |
| phrase | socially excluded | 0.797 | 0.777 | 0.671 | 5.325- | 4.496- | 4.330- | 2- | 169- |
| phrase | tasting bitter drinks | 0.753 | 0.740 | 0.638 | 4.564- | 4.049- | 4.031- | 0- | 2- |
| bench | def:arousal | 0.796 | 0.786 | 0.703 | 3.847- | 3.448- | 3.361- | 0- | 1380+ |
| bench | def:choice | 0.809 | 0.802 | 0.698 | 4.218- | 3.926- | 3.876- | 0- | 2349+ |
| bench | def:efficiency | 0.743 | 0.720 | 0.637 | 5.538- | 4.325- | 4.303- | 2- | 0- |
| bench | def:empathy | 0.785 | 0.777 | 0.673 | 4.023- | 3.711- | 3.638- | 0- | 341+ |
| bench | def:memory | 0.816 | 0.801 | 0.715 | 4.569- | 3.878- | 3.803- | 0- | 3208+ |
| bench | def:motor control | 0.793 | 0.780 | 0.697 | 3.984- | 3.417- | 3.449- | 0- | 738+ |
| bench | def:navigation | 0.774 | 0.766 | 0.683 | 4.594- | 4.192- | 4.091- | 0- | 96- |
| bench | def:retrieval | 0.789 | 0.779 | 0.701 | 4.518- | 4.037- | 3.876- | 0- | 812+ |
| bench | def:selective attention | 0.815 | 0.803 | 0.723 | 3.906- | 3.389- | 3.442- | 0- | 3208+ |
| bench | def:semantic memory | 0.770 | 0.759 | 0.667 | 4.570- | 4.118- | 4.001- | 0- | 26- |
| bench | being socially excluded in a ball-tossing gam | 0.808 | 0.782 | 0.643 | 6.206+ | 5.221+ | 4.879+ | 13+ | 76- |
| bench | disgust at rotten food | 0.795 | 0.765 | 0.647 | 6.082- | 4.886+ | 4.638+ | 7+ | 43- |
| bench | emotion regulation | 0.839 | 0.831 | 0.728 | 3.760- | 3.492- | 3.598- | 0- | 3208+ |
| bench | gambling with risky odds | 0.772 | 0.763 | 0.648 | 5.136- | 4.767+ | 4.395- | 3- | 35- |
| bench | getting chills from music | 0.773 | 0.748 | 0.636 | 5.729- | 4.690+ | 4.571+ | 6+ | 7- |
| bench | imagining future events | 0.787 | 0.775 | 0.652 | 4.930- | 4.498- | 4.382- | 0- | 77- |
| bench | judging the intentions of other people | 0.825 | 0.800 | 0.675 | 4.912- | 4.090- | 3.966- | 0- | 1146+ |
| bench | learning from rewards and punishments | 0.811 | 0.777 | 0.664 | 6.279+ | 4.836+ | 4.444- | 5+ | 179- |
| bench | learning to navigate a virtual city | 0.771 | 0.757 | 0.636 | 5.884- | 5.244+ | 4.985+ | 15+ | 17- |
| bench | mind wandering during rest | 0.816 | 0.803 | 0.689 | 4.843- | 4.333- | 4.266- | 0- | 881+ |
| bench | people playing video games | 0.799 | 0.786 | 0.682 | 4.697- | 4.180- | 4.103- | 0- | 360+ |
| bench | recalling childhood events | 0.791 | 0.778 | 0.668 | 4.184- | 3.742- | 3.670- | 0- | 247+ |
| bench | recollection | 0.802 | 0.787 | 0.682 | 4.468- | 3.900- | 3.918- | 0- | 385+ |
| bench | tapping fingers in sequence | 0.773 | 0.757 | 0.652 | 4.723- | 4.096- | 4.127- | 0- | 18- |
| bench | tasting sweet and bitter solutions | 0.775 | 0.761 | 0.653 | 4.779- | 4.216- | 4.253- | 0- | 21- |
| bench | the perception of music and melody | 0.820 | 0.808 | 0.698 | 5.017- | 4.503- | 4.358- | 1- | 1682+ |
| bench | waiting for a delayed monetary payoff | 0.754 | 0.737 | 0.621 | 5.663- | 4.952+ | 4.505- | 6+ | 1- |
| null | population of Canadian provinces | 0.793 | 0.783 | 0.708 | 4.540- | 4.021- | 3.977- | 0- | 867+ |
| null | golf handicap calculation | 0.804 | 0.783 | 0.699 | 4.499- | 3.607- | 3.624- | 0- | 1004+ |
| null | balancing chemical equations | 0.790 | 0.775 | 0.699 | 4.786- | 3.973- | 3.931- | 0- | 341+ |
| null | quarterly earnings report | 0.787 | 0.774 | 0.697 | 4.263- | 3.639- | 3.610- | 0- | 365+ |
| null | watercolor landscape painting | 0.801 | 0.773 | 0.668 | 5.377- | 4.235- | 4.286- | 1- | 71- |
| null | property tax assessment | 0.786 | 0.771 | 0.684 | 4.578- | 3.886- | 3.822- | 0- | 168- |
| null | periodic table of elements | 0.787 | 0.770 | 0.695 | 5.178- | 4.261- | 4.229- | 1- | 126- |
| null | python list comprehension | 0.811 | 0.768 | 0.665 | 6.487+ | 4.556- | 4.324- | 1- | 65- |

Gate top20 > 0.7618 (null p95) or > 0.7718 (null p99): studies of similar_study

| kind | text | top20 | old floor 0.75 | gate p95 | gate p99 |
|---|---|---|---|---|---|
| bench | tapping fingers in sequence | 0.7567 | 18 | 0 | 0 |
| phrase | socially excluded | 0.7773 | 169 | 3208 | 3208 |
| phrase | tasting bitter drinks | 0.7404 | 2 | 0 | 0 |
| bench | def:arousal | 0.7864 | 1380 | 3208 | 3208 |
| bench | def:choice | 0.8016 | 2349 | 3208 | 3208 |
| bench | def:efficiency | 0.7197 | 0 | 0 | 0 |
| bench | def:empathy | 0.7766 | 341 | 3208 | 3208 |
| bench | def:memory | 0.8007 | 3208 | 3208 | 3208 |
| bench | def:motor control | 0.7796 | 738 | 3208 | 3208 |
| bench | def:navigation | 0.7661 | 96 | 3208 | 0 |
| bench | def:retrieval | 0.7793 | 812 | 3208 | 3208 |
| bench | def:selective attention | 0.8026 | 3208 | 3208 | 3208 |
| bench | def:semantic memory | 0.7595 | 26 | 0 | 0 |
| bench | being socially excluded in a ball-tossing gam | 0.7818 | 76 | 3208 | 3208 |
| bench | disgust at rotten food | 0.7654 | 43 | 3208 | 0 |
| bench | emotion regulation | 0.8310 | 3208 | 3208 | 3208 |
| bench | gambling with risky odds | 0.7628 | 35 | 3208 | 0 |
| bench | getting chills from music | 0.7482 | 7 | 0 | 0 |
| bench | imagining future events | 0.7748 | 77 | 3208 | 3208 |
| bench | judging the intentions of other people | 0.8001 | 1146 | 3208 | 3208 |
| bench | learning from rewards and punishments | 0.7768 | 179 | 3208 | 3208 |
| bench | learning to navigate a virtual city | 0.7566 | 17 | 0 | 0 |
| bench | mind wandering during rest | 0.8030 | 881 | 3208 | 3208 |
| bench | people playing video games | 0.7858 | 360 | 3208 | 3208 |
| bench | recalling childhood events | 0.7776 | 247 | 3208 | 3208 |
| bench | recollection | 0.7866 | 385 | 3208 | 3208 |
| bench | tapping fingers in sequence | 0.7567 | 18 | 0 | 0 |
| bench | tasting sweet and bitter solutions | 0.7610 | 21 | 0 | 0 |
| bench | the perception of music and melody | 0.8075 | 1682 | 3208 | 3208 |
| bench | waiting for a delayed monetary payoff | 0.7370 | 1 | 0 | 0 |
| null | population of Canadian provinces | 0.7830 | 867 | 3208 | 3208 |
| null | golf handicap calculation | 0.7828 | 1004 | 3208 | 3208 |
| null | balancing chemical equations | 0.7747 | 341 | 3208 | 3208 |
| null | quarterly earnings report | 0.7738 | 365 | 3208 | 3208 |
| null | watercolor landscape painting | 0.7726 | 71 | 3208 | 3208 |
| null | property tax assessment | 0.7707 | 168 | 3208 | 0 |
| null | periodic table of elements | 0.7704 | 126 | 3208 | 0 |
| null | python list comprehension | 0.7679 | 65 | 3208 | 0 |

| top20 gate | threshold | check null FPR | check kept: all (cogat/bench/phrase) |
|---|---|---|---|
| null p90 | 0.7540 | 0.037 | 0.684 (0.66/0.86/0.91) |
| null p95 | 0.7618 | 0.030 | 0.584 (0.56/0.71/0.87) |
| null p99 | 0.7718 | 0.018 | 0.457 (0.43/0.64/0.77) |

gate top20 >= 0.76: check half, null FPR 0.037; kept cogat 0.59, bench 0.71, phrase 0.87; all in-domain 0.616; whole null 0.052

old floor as a gate (max >= 0.75, some study kept): null 0.314, in-domain 0.889
1-4 words: null 170, in-domain 133, median top20 0.734 / 0.784, AUC 0.907
5-9 words: null 39, in-domain 237, median top20 0.718 / 0.772, AUC 0.953
10-25 words: null 64, in-domain 545, median top20 0.698 / 0.766, AUC 0.981
26-10000 words: null 55, in-domain 343, median top20 0.719 / 0.762, AUC 0.934
centred top20: AUC on the check half 0.941 (raw 0.912)

typed in-domain texts failing ztop20_mad > 4.663 (82): def:arousal; def:choice; def:efficiency; def:empathy; def:memory; def:motor control; def:navigation; def:retrieval; def:selective attention; def:semantic memory; emotion regulation; imagining future events; judging the intentions of other people; mind wandering during rest; people playing video games; recalling childhood events; recollection; tapping fingers in sequence; tasting sweet and bitter solutions; the perception of music and melody; socially excluded; tasting bitter drinks; pain; listening to music; recognising familiar faces; remembering a list of words; holding digits in mind; stopping a planned movement; counting backwards; watching emotional film clips; smoking cravings; imagining a movement; speaking a second language; fear conditioning; extinction of fear; viewing faces with angry expressions; detecting an oddball tone; attending to one ear; resting with eyes closed; mindfulness meditation

typed in-domain texts failing zmax_mad > 6.187 (114): def:arousal; def:choice; def:efficiency; def:empathy; def:memory; def:motor control; def:navigation; def:retrieval; def:selective attention; def:semantic memory; disgust at rotten food; emotion regulation; gambling with risky odds; getting chills from music; imagining future events; judging the intentions of other people; learning to navigate a virtual city; mind wandering during rest; people playing video games; recalling childhood events; recollection; tapping fingers in sequence; tasting sweet and bitter solutions; the perception of music and melody; waiting for a delayed monetary payoff; socially excluded; tasting bitter drinks; visual word form area; pain; reward anticipation; listening to music; reading words aloud; recognising familiar faces; remembering a list of words; holding digits in mind; stopping a planned movement; counting backwards; watching emotional film clips; looking at pictures of food; smoking cravings

typed in-domain texts failing max > 0.789 (37): def:efficiency; def:empathy; def:navigation; def:semantic memory; gambling with risky odds; getting chills from music; imagining future events; learning to navigate a virtual city; tapping fingers in sequence; tasting sweet and bitter solutions; waiting for a delayed monetary payoff; tasting bitter drinks; reading words aloud; holding digits in mind; counting backwards; learning a motor sequence; imagining a movement; speaking a second language; choosing between smaller sooner and larg; viewing faces with angry expressions; detecting an oddball tone; attending to one ear; resting with eyes closed; navigating a maze; recognising objects by touch; heat pain on the forearm; itch; looking at pictures of spiders; humour and laughing at jokes; predicting the next tone; semantic judgements about words; playing the piano; reading music notation; numerical comparison; the go/no-go task; the n-back task; probabilistic learning from feedback

hubness: share of the 1259 in-domain texts whose top 5% holds a study: max 0.77, 10th 0.63, 100th 0.45, median 0.021; studies in >= 50%: 51, in >= 30%: 808, in none: 5069
