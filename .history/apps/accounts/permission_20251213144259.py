"""
Docstring for apps.accounts.permission
"""
#函数用于判断该用户的类型（Utilisateur, cheffe, administratrice,guest）
def is_user(user):
    return user.role == 'user'  

def is_cheffe(user):
    return user.role == 'cheffe'    

def is_administratrice(user):
    return user.role == 'administratrice'   

def is_guest(user):
    return user.role == 'guest'
