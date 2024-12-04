import matplotlib.pyplot as plt
import numpy as np

# Given times in hours and minutes (converted to decimal hours)
given_times = [
    6 + 1/60,    # 06:01 AM
    6 + 40/60,   # 06:40 AM
    7 + 30/60,   # 07:30 AM
    7 + 8/60     # 07:08 AM
]

# Days from 1 to 19
days = np.arange(1, 20)

# Initialize the list of times with the given times
times = given_times.copy()

# Generate dummy times for the remaining days (between 6:00 AM and 8:00 AM)
np.random.seed(0)  # For reproducibility
dummy_times = np.random.uniform(6, 8, size=15)
times.extend(dummy_times)

# Ensure we have a time for each day
assert len(times) == len(days), "Number of times does not match number of days."

# Prepare the event times for each day
event_times = [[t] for t in times]

# Create the raster plot
plt.figure(figsize=(12, 6))
plt.eventplot(event_times, orientation='horizontal', colors='black', linelengths=0.8, lineoffsets=days)

# Customize the plot
plt.xlabel('Time of Day (hours)')
plt.ylabel('Day')
plt.title('Raster Plot of Core Body Temperature Events')
plt.xlim(0, 24)
plt.xticks(np.arange(0, 25, 1))
plt.ylim(0.5, 19.5)
plt.yticks(days)

# Display the plot
plt.show()
