# Composition Entity Linker (under development)

This is a tool for linking classical music record & track to the corresponding composition / movement, useful in cleaning up metadata in classical music datasets. Inputs are referenced through corpus crawled from https://imslp.org/wiki/Main_Page. 

package on pypi: https://pypi.org/project/composition-entity-linker/ 

### Install 
```pip install composition-entity-linker```

### Usage 
```
from composition_entity_linker import CELlinker, Track
linker = CELlinker()
```

#### 1. Query the composition from track name:
```
track = Track("Violin Sonata in A Major, Op. 162, D. 574 ""Grand Duo"": III. Andantino (Live)", composer="Franz Schubert")
result = linker.query(track)
"""
result: {
    "found_flag": True,
    "composition": "Violin Sonata in A major, D.574"
    "movement": "Andantino"
}
"""
```

#### 2. Compare if the two tracks are refering to the same composition: 
```
track1 = Track("Prelude and Fugue No. 2 in C Minor BWV 847", composer="Johann Sebastian Bach")
track2 = Track("Prelude & Fugue In C Minor (Well-Tempered Clavier, Book I, No. 2), BWV 847", composer="J.S. Bach")
linker.compare(track1, track2)
# return: True


track3 = Track("Das Wohltemperierte Klavier: Book 1, BWV 846-869: Fugue in C minor BWV 847", composer="Иоганн Себастьян Бах")
linker.compare(track1, track3)
# return: True

```

### Track info
Although only the title is required, inputing composer name will improve matching accuracy and speed.

```
Track(title: str, 
    duration: float in ms,
    composer: str)
```

