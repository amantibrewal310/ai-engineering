# Strategy B: Constrained Prompt (JSON)

## Review #1

> The new smartphone is amazing, the camera quality is top-notch but the battery life is a bit disappointing. I love the design though!

- **Unique Responses:** 1 / 5
- **Consistency Score:** 100.0%

### Prompt

````text
Analyze the sentiment of the following review: The new smartphone is amazing, the camera quality is top-notch but the battery life is a bit disappointing. I love the design though!

Output only a JSON object matching this schema:
```json
{
    "sentiment": ("positive","negative","mixed"),
    "confidence": ("Low", "Medium", "High"),
    "key_aspects": list of exact phrases quoted directly from the review (no abstract summaries)
}
```
````

### Responses

#### Run 1

```json
{
    "sentiment": "mixed",
    "confidence": "High",
    "key_aspects": [
        "amazing",
        "camera quality is top-notch",
        "battery life is a bit disappointing",
        "love the design"
    ]
}
```

#### Run 2

```json
{
    "sentiment": "mixed",
    "confidence": "High",
    "key_aspects": [
        "amazing",
        "camera quality is top-notch",
        "battery life is a bit disappointing",
        "love the design"
    ]
}
```

#### Run 3

```json
{
    "sentiment": "mixed",
    "confidence": "High",
    "key_aspects": [
        "amazing",
        "camera quality is top-notch",
        "battery life is a bit disappointing",
        "love the design"
    ]
}
```

#### Run 4

```json
{
    "sentiment": "mixed",
    "confidence": "High",
    "key_aspects": [
        "amazing",
        "camera quality is top-notch",
        "battery life is a bit disappointing",
        "love the design"
    ]
}
```

#### Run 5

```json
{
    "sentiment": "mixed",
    "confidence": "High",
    "key_aspects": [
        "amazing",
        "camera quality is top-notch",
        "battery life is a bit disappointing",
        "love the design"
    ]
}
```

---

## Review #2

> Bus left on time, seats were clean and the driver was polite. Great trip!

- **Unique Responses:** 1 / 5
- **Consistency Score:** 100.0%

### Prompt

````text
Analyze the sentiment of the following review: Bus left on time, seats were clean and the driver was polite. Great trip!

Output only a JSON object matching this schema:
```json
{
    "sentiment": ("positive","negative","mixed"),
    "confidence": ("Low", "Medium", "High"),
    "key_aspects": list of exact phrases quoted directly from the review (no abstract summaries)
}
```
````

### Responses

#### Run 1

```json
{
    "sentiment": "positive",
    "confidence": "High",
    "key_aspects": [
        "Bus left on time",
        "seats were clean",
        "driver was polite",
        "Great trip!"
    ]
}
```

#### Run 2

```json
{
    "sentiment": "positive",
    "confidence": "High",
    "key_aspects": [
        "Bus left on time",
        "seats were clean",
        "driver was polite",
        "Great trip!"
    ]
}
```

#### Run 3

```json
{
    "sentiment": "positive",
    "confidence": "High",
    "key_aspects": [
        "Bus left on time",
        "seats were clean",
        "driver was polite",
        "Great trip!"
    ]
}
```

#### Run 4

```json
{
    "sentiment": "positive",
    "confidence": "High",
    "key_aspects": [
        "Bus left on time",
        "seats were clean",
        "driver was polite",
        "Great trip!"
    ]
}
```

#### Run 5

```json
{
    "sentiment": "positive",
    "confidence": "High",
    "key_aspects": [
        "Bus left on time",
        "seats were clean",
        "driver was polite",
        "Great trip!"
    ]
}
```

---

## Review #3

> The hotel room smelled of damp and nobody answered the reception phone all night.

- **Unique Responses:** 1 / 5
- **Consistency Score:** 100.0%

### Prompt

````text
Analyze the sentiment of the following review: The hotel room smelled of damp and nobody answered the reception phone all night.

Output only a JSON object matching this schema:
```json
{
    "sentiment": ("positive","negative","mixed"),
    "confidence": ("Low", "Medium", "High"),
    "key_aspects": list of exact phrases quoted directly from the review (no abstract summaries)
}
```
````

### Responses

#### Run 1

```json
{
    "sentiment": "negative",
    "confidence": "High",
    "key_aspects": [
        "smelled of damp",
        "nobody answered the reception phone all night"
    ]
}
```

#### Run 2

```json
{
    "sentiment": "negative",
    "confidence": "High",
    "key_aspects": [
        "smelled of damp",
        "nobody answered the reception phone all night"
    ]
}
```

#### Run 3

```json
{
    "sentiment": "negative",
    "confidence": "High",
    "key_aspects": [
        "smelled of damp",
        "nobody answered the reception phone all night"
    ]
}
```

#### Run 4

```json
{
    "sentiment": "negative",
    "confidence": "High",
    "key_aspects": [
        "smelled of damp",
        "nobody answered the reception phone all night"
    ]
}
```

#### Run 5

```json
{
    "sentiment": "negative",
    "confidence": "High",
    "key_aspects": [
        "smelled of damp",
        "nobody answered the reception phone all night"
    ]
}
```

---

