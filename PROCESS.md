# Process

## Tools

I used **Python, Matplotlib, HTML Canvas / JavaScript, uv, VS Code, GitHub Desktop, and ChatGPT** during this project.

Python was used for reading and filtering the data, calculating movement, and generating the static and animated outputs. Matplotlib was used for the main visualisations. HTML Canvas / JavaScript was used for the interactive webpage, including trajectory drawing, zooming, hover interaction, and time-based animation. I used `uv` to run the scripts, VS Code to edit code and Markdown files, and GitHub Desktop to record development through commits and pushes.

ChatGPT was mainly used to help translate my visual and interaction ideas into Python / JavaScript code, explain programming steps, identify errors, and revise implementations after I tested them. I did not treat generated code as a final answer. I repeatedly ran the scripts, checked the data logic, visual result, and interaction performance, then decided what should be changed.

The choice of dataset, research focus, data interpretation, visual direction, and final decisions about what to keep or reject were my own. I selected the Kruger elephant tracking dataset because it contains timestamp, GPS location, individual identifier, and external temperature, which made it suitable for exploring movement rhythm.

I also checked the data before visualising it. The raw dataset contains **283,688 GPS observations from 14 tracked individuals**. I examined the sampling intervals and found that most records are approximately 30 minutes apart, but longer gaps also occur. This meant that not all consecutive records could be compared directly.

## Kept

I kept a method based on straight-line displacement between consecutive GPS records approximately 30 minutes apart.

To make movement steps more comparable, I used only consecutive records with a time interval of **29–31 minutes** and calculated Haversine distance between the two GPS locations. This produced **253,203 valid movement steps** and avoided mixing normal sampling intervals with longer gaps.

I also inspected the movement distribution rather than automatically deleting large displacement values. Some larger steps and jump-return patterns appeared suspicious, but a large displacement alone was not enough to prove that a record was wrong. I therefore avoided applying an arbitrary distance threshold and kept the original records.

The temporal analysis revealed a clear daily rhythm: median displacement was lowest before dawn and higher around **16:00–17:00**. Comparing hourly rhythms across calendar months showed that peak timing remained relatively stable while peak intensity changed.

This became the main visual idea:

**Stable timing, changing intensity.**

I kept three final forms because they communicate different parts of the project: the GIF shows how the 24-hour rhythm unfolds over time, the static visual summarises the daily and monthly patterns, and the interactive webpage connects the collective movement landscape with individual trajectories.

## Rejected

I explored several directions that were not kept in the final result.

First, I tested the relationship between external temperature and movement. Although movement appeared higher in some warmer temperature ranges, further comparison with hourly patterns showed that temperature was strongly entangled with time of day. Similar temperatures could correspond to very different movement levels, so I rejected a causal interpretation such as “higher temperature causes more movement” and focused instead on temporal rhythm.

Second, I experimented with terrain and elevation, including density-based pseudo terrain and real DEM terrain data. These versions added geographical texture, but they also increased visual complexity without making the movement rhythm easier to understand. I therefore removed terrain and returned the visual focus to the movement data itself.

Finally, I tested a stronger interactive style with thicker, brighter green movement lines and glow effects. Although the active movement became more visible, the webpage became noticeably slower and the visual result felt less refined. Because the change added visual weight but no new information, I restored the lighter and smoother version.

These rejected experiments helped clarify that the final visual should not simply contain more effects, but should make the underlying data pattern easier to understand.