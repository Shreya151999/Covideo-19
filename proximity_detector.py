import math

# function that receives the model output.
# masked and not_masked are two dictionaries
# having the ID of each face (masked or bare) as
# keys, the coordinates of the boxes containing the
# faces as values (i.e. ID 3 => [0, 200, 0, 200]).
# coordinates are expressed as [xmin, xmax, ymin, ymax].
def proximity_detector(masked, not_masked):
    result = set()
    std_ratio = 2 / 3 # standard parameter
    std_face_width = 0.16 # standard face width in meters

    # is there anyone that does not have a mask? If yes, verify that no one is close to him!
    for item in not_masked.items():
        first_width = item[1][1] - item[1][0]
        first_height = item[1][3] - item[1][2]
        first_max = max(first_width, first_height)
        first = (item[1][0] + first_width / 2, item[1][2] + first_height / 2) # x,y coordinates of NM's centroid

        # are there any masked people close to the one who's not masked?
        for m in masked.items():
            second_width = m[1][1] - m[1][0]
            second_height = m[1][3] - m[1][2]
            second_max = max(second_width, second_height)
            second = (m[1][0] + second_width / 2, m[1][2] + second_height / 2) # x,y coordinates of M's centroid
            if (first_max <= second_max and first_max > second_max * std_ratio) or\
               (second_max < first_max and second_max > first_max * std_ratio): # are the faces' depths comparable?
                distance = math.sqrt((first[0] - second[0])**2 + (first[1] - second[1])**2)
                if distance / ((first_max + second_max) / 2) < 1 / std_face_width: # people are too close to each other!
                    result.add(tuple(sorted(('NM{}'.format(item[0]), 'M{}'.format(m[0]))))) # tuple+sorted combo is for preventing simmetries

        # are there any unmasked people close to the one who's not masked?
        for nm in not_masked.items():
            if nm[0] != item[0]:
                second_width = nm[1][1] - nm[1][0]
                second_height = nm[1][3] - nm[1][2]
                second_max = max(second_width, second_height)
                second = (nm[1][0] + second_width / 2, nm[1][2] + second_height / 2) # x,y coordinates of M's centroid
                if (first_max <= second_max and first_max > second_max * std_ratio) or\
                   (second_max < first_max and second_max > first_max * std_ratio): # are the faces' depths comparable?
                    distance = math.sqrt((first[0] - second[0])**2 + (first[1] - second[1])**2)
                    if distance / ((first_max + second_max) / 2) < 1 / std_face_width: # people are too close to each other!
                        result.add(tuple(sorted(('NM{}'.format(item[0]), 'NM{}'.format(nm[0]))))) # tuple+sorted combo is for preventing simmetries

    return result
