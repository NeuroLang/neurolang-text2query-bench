texts: null 328, cogat 1138, bench 27, phrase 94; studies 14371
median score: null 0.640, in-domain 0.677; range of medians 0.574-0.762

| statistic | AUC fit | AUC fit typed | null p95 | null p99 | check FPR@p99 | check keep@p99 (cogat/bench/phrase) | check FPR@p95 | check keep@p95 |
|---|---|---|---|---|---|---|---|---|
| max | 0.920 | 0.959 | 0.7675 | 0.7814 | 0.006 | 0.437 (0.40/0.64/0.79) | 0.024 | 0.619 |
| top20 | 0.934 | 0.962 | 0.7503 | 0.7626 | 0.000 | 0.484 (0.46/0.64/0.74) | 0.024 | 0.627 |
| median | 0.855 | 0.866 | 0.6803 | 0.6931 | 0.012 | 0.276 (0.26/0.36/0.45) | 0.012 | 0.451 |
| top20-median | 0.829 | 0.942 | 0.0828 | 0.0880 | 0.006 | 0.314 (0.28/0.43/0.68) | 0.043 | 0.457 |
| zmax_mad | 0.537 | 0.761 | 4.8835 | 5.5189 | 0.012 | 0.029 (0.02/0.07/0.06) | 0.055 | 0.129 |
| zmax_sd | 0.510 | 0.731 | 4.8428 | 5.4748 | 0.012 | 0.014 (0.01/0.00/0.06) | 0.061 | 0.087 |
| ztop20_mad | 0.617 | 0.828 | 3.7066 | 3.9313 | 0.030 | 0.143 (0.11/0.36/0.43) | 0.073 | 0.287 |
| ztop20_sd | 0.599 | 0.818 | 3.6529 | 3.8351 | 0.012 | 0.114 (0.09/0.36/0.38) | 0.067 | 0.217 |
| n(zmad>=3) | 0.649 | 0.825 | 51.8500 | 70.5900 | 0.018 | 0.208 (0.18/0.43/0.45) | 0.061 | 0.305 |
| n(zsd>=3) | 0.642 | 0.827 | 44.8500 | 54.7400 | 0.018 | 0.183 (0.16/0.36/0.45) | 0.049 | 0.279 |
| n(zmad>=4) | 0.587 | 0.822 | 4.0000 | 6.3700 | 0.043 | 0.144 (0.11/0.36/0.45) | 0.061 | 0.205 |
| n(zsd>=4) | 0.551 | 0.786 | 3.0000 | 5.0000 | 0.024 | 0.105 (0.07/0.36/0.40) | 0.043 | 0.168 |
| n(zmad>=5) | 0.531 | 0.634 | 0.0000 | 1.0000 | 0.012 | 0.048 (0.04/0.07/0.15) | 0.049 | 0.106 |
| n(zsd>=5) | 0.507 | 0.557 | 0.0000 | 1.0000 | 0.012 | 0.022 (0.02/0.00/0.04) | 0.037 | 0.059 |
| n(zmad>=6) | 0.500 | 0.514 | 0.0000 | 0.0000 | 0.012 | 0.010 (0.01/0.00/0.02) | 0.012 | 0.010 |
| n(zsd>=6) | 0.498 | 0.505 | 0.0000 | 0.0000 | 0.012 | 0.005 (0.00/0.00/0.02) | 0.012 | 0.005 |
| old floor: top5%>=0.75 | 0.883 | 0.932 | 8.2500 | 40.7000 | 0.006 | 0.483 (0.46/0.57/0.72) | 0.024 | 0.632 |

Short phrases, bench topics and the null's highest (gate at the fit null's 99th percentile):

| kind | text | max | top20 | median | zmax_mad | ztop20_mad | ztop20_sd | n(zmad>=5) | old floor: top5%>=0.75 |
|---|---|---|---|---|---|---|---|---|---|
| bench | tapping fingers in sequence | 0.773 | 0.745 | 0.658 | 4.536- | 3.460- | 3.501- | 0- | 5- |
| phrase | socially excluded | 0.797 | 0.763 | 0.670 | 5.352- | 3.907- | 3.840+ | 1- | 28- |
| phrase | tasting bitter drinks | 0.747 | 0.729 | 0.639 | 4.332- | 3.619- | 3.585- | 0- | 0- |
| bench | def:arousal | 0.790 | 0.775 | 0.705 | 3.901- | 3.192- | 3.113- | 0- | 293+ |
| bench | def:choice | 0.807 | 0.793 | 0.706 | 3.902- | 3.381- | 3.348- | 0- | 719+ |
| bench | def:efficiency | 0.734 | 0.706 | 0.636 | 5.200- | 3.731- | 3.699- | 1- | 0- |
| bench | def:empathy | 0.780 | 0.769 | 0.679 | 3.862- | 3.436- | 3.265- | 0- | 127+ |
| bench | def:memory | 0.801 | 0.791 | 0.719 | 3.768- | 3.294- | 3.239- | 0- | 719+ |
| bench | def:motor control | 0.782 | 0.770 | 0.698 | 3.456- | 2.983- | 3.012- | 0- | 181+ |
| bench | def:navigation | 0.769 | 0.755 | 0.683 | 4.119- | 3.461- | 3.428- | 0- | 18- |
| bench | def:retrieval | 0.788 | 0.776 | 0.702 | 4.346- | 3.719- | 3.524- | 0- | 262+ |
| bench | def:selective attention | 0.811 | 0.798 | 0.729 | 3.748- | 3.160- | 3.146- | 0- | 719+ |
| bench | def:semantic memory | 0.767 | 0.751 | 0.670 | 4.280- | 3.579- | 3.485- | 0- | 9- |
| bench | being socially excluded in a ball-tossing gam | 0.798 | 0.763 | 0.645 | 5.659+ | 4.360+ | 4.115+ | 2+ | 16- |
| bench | disgust at rotten food | 0.776 | 0.751 | 0.647 | 5.155- | 4.156+ | 4.011+ | 1- | 9- |
| bench | emotion regulation | 0.838 | 0.823 | 0.729 | 3.930- | 3.395- | 3.440- | 0- | 719+ |
| bench | gambling with risky odds | 0.771 | 0.755 | 0.648 | 5.114- | 4.445+ | 4.113+ | 3+ | 14- |
| bench | getting chills from music | 0.756 | 0.732 | 0.640 | 5.153- | 4.102+ | 3.902+ | 2+ | 2- |
| bench | imagining future events | 0.787 | 0.772 | 0.657 | 4.794- | 4.263+ | 4.154+ | 0- | 32- |
| bench | judging the intentions of other people | 0.804 | 0.791 | 0.685 | 4.100- | 3.651- | 3.489- | 0- | 367+ |
| bench | learning from rewards and punishments | 0.781 | 0.765 | 0.664 | 4.756- | 4.109+ | 3.859+ | 0- | 39- |
| bench | learning to navigate a virtual city | 0.759 | 0.746 | 0.639 | 5.120- | 4.534+ | 4.383+ | 1- | 4- |
| bench | mind wandering during rest | 0.815 | 0.792 | 0.690 | 4.902- | 4.003+ | 3.866+ | 0- | 230+ |
| bench | people playing video games | 0.791 | 0.772 | 0.686 | 4.613- | 3.790- | 3.708- | 0- | 76+ |
| bench | recalling childhood events | 0.785 | 0.770 | 0.673 | 4.066- | 3.543- | 3.447- | 0- | 68+ |
| bench | recollection | 0.801 | 0.780 | 0.688 | 4.322- | 3.523- | 3.537- | 0- | 119+ |
| bench | tapping fingers in sequence | 0.773 | 0.745 | 0.658 | 4.536- | 3.460- | 3.501- | 0- | 5- |
| bench | tasting sweet and bitter solutions | 0.762 | 0.745 | 0.654 | 4.253- | 3.580- | 3.605- | 0- | 6- |
| bench | the perception of music and melody | 0.816 | 0.799 | 0.702 | 5.010- | 4.272+ | 3.995+ | 1- | 504+ |
| bench | waiting for a delayed monetary payoff | 0.743 | 0.730 | 0.623 | 4.933- | 4.429+ | 4.003+ | 0- | 0- |
| null | golf handicap calculation | 0.795 | 0.772 | 0.702 | 4.015- | 3.009- | 3.078- | 0- | 266+ |
| null | quarterly earnings report | 0.780 | 0.763 | 0.694 | 3.990- | 3.202- | 3.195- | 0- | 47+ |
| null | property tax assessment | 0.784 | 0.762 | 0.684 | 4.443- | 3.479- | 3.422- | 0- | 37- |
| null | population of Canadian provinces | 0.773 | 0.760 | 0.702 | 3.910- | 3.189- | 3.210- | 0- | 54+ |
| null | balancing chemical equations | 0.771 | 0.759 | 0.694 | 4.106- | 3.485- | 3.487- | 0- | 27- |
| null | watercolor landscape painting | 0.788 | 0.757 | 0.674 | 4.650- | 3.392- | 3.499- | 0- | 16- |
| null | python list comprehension | 0.768 | 0.756 | 0.669 | 4.464- | 3.948+ | 3.709- | 0- | 15- |
| null | crochet amigurumi pattern | 0.773 | 0.756 | 0.693 | 4.354- | 3.399- | 3.336- | 0- | 20- |

Gate top20 > 0.7503 (null p95) or > 0.7626 (null p99): studies of similar_study

| kind | text | top20 | old floor 0.75 | gate p95 | gate p99 |
|---|---|---|---|---|---|
| bench | tapping fingers in sequence | 0.7455 | 5 | 0 | 0 |
| phrase | socially excluded | 0.7627 | 28 | 719 | 719 |
| phrase | tasting bitter drinks | 0.7295 | 0 | 0 | 0 |
| bench | def:arousal | 0.7747 | 293 | 719 | 719 |
| bench | def:choice | 0.7932 | 719 | 719 | 719 |
| bench | def:efficiency | 0.7065 | 0 | 0 | 0 |
| bench | def:empathy | 0.7691 | 127 | 719 | 719 |
| bench | def:memory | 0.7911 | 719 | 719 | 719 |
| bench | def:motor control | 0.7702 | 181 | 719 | 719 |
| bench | def:navigation | 0.7550 | 18 | 719 | 0 |
| bench | def:retrieval | 0.7756 | 262 | 719 | 719 |
| bench | def:selective attention | 0.7981 | 719 | 719 | 719 |
| bench | def:semantic memory | 0.7514 | 9 | 719 | 0 |
| bench | being socially excluded in a ball-tossing gam | 0.7627 | 16 | 719 | 719 |
| bench | disgust at rotten food | 0.7513 | 9 | 719 | 0 |
| bench | emotion regulation | 0.8232 | 719 | 719 | 719 |
| bench | gambling with risky odds | 0.7549 | 14 | 719 | 0 |
| bench | getting chills from music | 0.7323 | 2 | 0 | 0 |
| bench | imagining future events | 0.7722 | 32 | 719 | 719 |
| bench | judging the intentions of other people | 0.7913 | 367 | 719 | 719 |
| bench | learning from rewards and punishments | 0.7654 | 39 | 719 | 719 |
| bench | learning to navigate a virtual city | 0.7456 | 4 | 0 | 0 |
| bench | mind wandering during rest | 0.7916 | 230 | 719 | 719 |
| bench | people playing video games | 0.7722 | 76 | 719 | 719 |
| bench | recalling childhood events | 0.7704 | 68 | 719 | 719 |
| bench | recollection | 0.7804 | 119 | 719 | 719 |
| bench | tapping fingers in sequence | 0.7455 | 5 | 0 | 0 |
| bench | tasting sweet and bitter solutions | 0.7450 | 6 | 0 | 0 |
| bench | the perception of music and melody | 0.7994 | 504 | 719 | 719 |
| bench | waiting for a delayed monetary payoff | 0.7303 | 0 | 0 | 0 |
| null | golf handicap calculation | 0.7721 | 266 | 719 | 719 |
| null | quarterly earnings report | 0.7628 | 47 | 719 | 719 |
| null | property tax assessment | 0.7624 | 37 | 719 | 0 |
| null | population of Canadian provinces | 0.7604 | 54 | 719 | 0 |
| null | balancing chemical equations | 0.7594 | 27 | 719 | 0 |
| null | watercolor landscape painting | 0.7568 | 16 | 719 | 0 |
| null | python list comprehension | 0.7563 | 15 | 719 | 0 |
| null | crochet amigurumi pattern | 0.7556 | 20 | 719 | 0 |

| top20 gate | threshold | check null FPR | check kept: all (cogat/bench/phrase) |
|---|---|---|---|
| null p90 | 0.7393 | 0.055 | 0.776 (0.76/0.86/0.94) |
| null p95 | 0.7503 | 0.024 | 0.627 (0.60/0.79/0.85) |
| null p99 | 0.7626 | 0.000 | 0.484 (0.46/0.64/0.74) |

gate top20 >= 0.75: check half, null FPR 0.024; kept cogat 0.61, bench 0.79, phrase 0.85; all in-domain 0.633; whole null 0.040

old floor as a gate (max >= 0.75, some study kept): null 0.131, in-domain 0.829
1-4 words: null 170, in-domain 133, median top20 0.718 / 0.775, AUC 0.923
5-9 words: null 39, in-domain 237, median top20 0.704 / 0.764, AUC 0.969
10-25 words: null 64, in-domain 545, median top20 0.687 / 0.759, AUC 0.985
26-10000 words: null 55, in-domain 343, median top20 0.705 / 0.755, AUC 0.961
centred top20: AUC on the check half 0.955 (raw 0.939)

typed in-domain texts failing ztop20_mad > 3.931 (65): def:arousal; def:choice; def:efficiency; def:empathy; def:memory; def:motor control; def:navigation; def:retrieval; def:selective attention; def:semantic memory; emotion regulation; judging the intentions of other people; people playing video games; recalling childhood events; recollection; tapping fingers in sequence; tasting sweet and bitter solutions; socially excluded; tasting bitter drinks; visual word form area; recognising familiar faces; remembering a list of words; holding digits in mind; stopping a planned movement; counting backwards; watching emotional film clips; imagining a movement; speaking a second language; judging whether a face is trustworthy; fear conditioning; detecting an oddball tone; attending to one ear; hypnosis; thinking about oneself; punishing unfair offers; craving cocaine; alcohol dependence; depressed patients; recognising objects by touch; smelling odours

typed in-domain texts failing zmax_mad > 5.519 (113): def:arousal; def:choice; def:efficiency; def:empathy; def:memory; def:motor control; def:navigation; def:retrieval; def:selective attention; def:semantic memory; disgust at rotten food; emotion regulation; gambling with risky odds; getting chills from music; imagining future events; judging the intentions of other people; learning from rewards and punishments; learning to navigate a virtual city; mind wandering during rest; people playing video games; recalling childhood events; recollection; tapping fingers in sequence; tasting sweet and bitter solutions; the perception of music and melody; waiting for a delayed monetary payoff; socially excluded; tasting bitter drinks; visual word form area; pain; reward anticipation; listening to music; reading words aloud; recognising familiar faces; remembering a list of words; holding digits in mind; stopping a planned movement; counting backwards; watching emotional film clips; looking at pictures of food

typed in-domain texts failing max > 0.781 (36): def:efficiency; def:empathy; def:navigation; def:semantic memory; disgust at rotten food; gambling with risky odds; getting chills from music; learning from rewards and punishments; learning to navigate a virtual city; tapping fingers in sequence; tasting sweet and bitter solutions; waiting for a delayed monetary payoff; tasting bitter drinks; reading words aloud; remembering a list of words; holding digits in mind; counting backwards; learning a motor sequence; imagining a movement; speaking a second language; choosing between smaller sooner and larg; viewing faces with angry expressions; detecting an oddball tone; attending to one ear; resting with eyes closed; navigating a maze; recognising objects by touch; heat pain on the forearm; itch; looking at pictures of spiders; predicting the next tone; playing the piano; recognising emotional voices; attention deficit hyperactivity; reading music notation; probabilistic learning from feedback

hubness: share of the 1259 in-domain texts whose top 5% holds a study: max 0.69, 10th 0.43, 100th 0.29, median 0.030; studies in >= 50%: 4, in >= 30%: 88, in none: 462
