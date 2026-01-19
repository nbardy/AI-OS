import matplotlib.pyplot as plt

data = [
    {'country': 'Country A', 'left_handed': 10, 'ambidextrous': 5},
    {'country': 'Country B', 'left_handed': 15, 'ambidextrous': 3},
    {'country': 'Country C', 'left_handed': 12, 'ambidextrous': 7},
]

fig, ax = plt.subplots(figsize=(8, 6))

x = [d['country'] for d in data]
left_handed = [d['left_handed'] for d in data]
ambidextrous = [d['ambidextrous'] for d in data]

ax.bar(x, left_handed, label='Left-handed')
ax.bar(x, ambidextrous, bottom=left_handed, label='Ambidextrous')

ax.set_title('Handedness Distribution')
ax.set_xlabel('Country')
ax.set_ylabel('Percentage')

ax.legend()

plt.savefig('chart.png')