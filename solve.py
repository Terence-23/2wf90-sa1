##
# 2WF90 Algebra for Security -- Software Assignment 1 
# Integer and Modular Arithmetic
# solve.py
#
#
# Group number:
# group_number 
#
# Author names and student IDs:
# author_name_1 (author_student_ID_1) 
# author_name_2 (author_student_ID_2)
# author_name_3 (author_student_ID_3)
# author_name_4 (author_student_ID_4)
##

# Import built-in json library for handling input/output 
import json



def solve_exercise(exercise_location : str, answer_location : str):
    """
    solves an exercise specified in the file located at exercise_location and
    writes the answer to a file at answer_location. Note: the file at
    answer_location might not exist yet and, hence, might still need to be created.
    """
    
    # Open file at exercise_location for reading.
    with open(exercise_location, "r") as exercise_file:
        # Deserialize JSON exercise data present in exercise_file to corresponding Python exercise data 
        exercise = json.load(exercise_file)
        

    ### Parse and solve ###

    # Check type of exercise
    if exercise["type"] == "integer_arithmetic":
        # Check what operation within the integer arithmetic operations we need to solve
        if exercise["operation"] == "addition":
            # Solve integer arithmetic addition exercise
            pass
        elif exercise["operation"] == "subtraction":
            # Solve integer arithmetic subtraction exercise
            pass
        # et cetera
    else: # exercise["type"] == "modular_arithmetic"
        # Check what operation within the modular arithmetic operations we need to solve
        if exercise["operation"] == "reduction":
            # Solve modular arithmetic reduction exercise
            pass
        # et cetera


    # Open file at answer_location for writing, creating the file if it does not exist yet
    # (and overwriting it if it does already exist).
    with open(answer_location, "w") as answer_file:
        # Serialize Python answer data (stored in answer) to JSON answer data and write it to answer_file
        json.dump(answer, answer_file, indent=4)

# You can call your function from here
# Please do not *run* code outside this block
# You can however define other functions or constants
if __name__ == '__main__':
    solve_exercise('Simple/Exercises/exercise0.json', 'Simple/Answers/answer0.json')