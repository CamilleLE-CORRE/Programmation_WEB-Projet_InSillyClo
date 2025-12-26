"""
The function is used to determine the user's type: Utilisateur, cheffe, administratrice,guest
"""

def is_utilisateur(user):
    return user.role == 'user'  

def is_cheffe(user):
    return user.role == 'cheffe'    

def is_administratrice(user):
    return user.role == 'administratrice'   

def is_guest(user):
    return user.role == 'guest'
