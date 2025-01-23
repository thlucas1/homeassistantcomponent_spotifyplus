from copy import deepcopy

# # get smartinspect logger reference; create a new session for this module name.
# from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIColors
# import logging
# _logsi:SISession = SIAuto.Si.GetSession(__name__)
# if (_logsi == None):
#     _logsi = SIAuto.Si.AddSession(__name__, True)
# _logsi.SystemLogger = logging.getLogger(__name__)

def passwordMaskDictionary(inputObj:dict) -> dict:
    """
    Checks keys in a dictionary any keys that contain `password` and masks the
    value so that the password is not displayed in a trace file.

    Args:
        inputObj (dict):
            Dictionary object to check.
    
    Returns:
        A copy of the `inputObj` source dictionary with passwor(s) masked.
        
    Note that this method performs a simple copy of the dictionary.
    """
    # if input is null then don't bother.
    if (inputObj is None):
        return inputObj
    
    # create a new dictionary.
    result:dict = {}
    
    # process keys in the dictionary.
    key:str
    for key in inputObj.keys():
        keyLower:str = key.lower()
        if (keyLower.find('password') == -1):
            result[key] = inputObj[key]
        else:
            value:str = inputObj[key]
            if (value is not None) and (isinstance(value, str)):
                result[key] = ''.ljust(len(value), '*')
                
    return result
    

def passwordMaskString(inputObj:str) -> str:
    """
    Checks a string for a password value and masks the value so that the password is not displayed 
    in a trace file.

    Args:
        inputObj (str):
            String object to check.
    
    Returns:
        A copy of the `inputObj` value with password masked.
    """
    # if input is null then don't bother.
    if (inputObj is None):
        return inputObj
    
    # create a new value.
    result:str = ''.ljust(len(inputObj), '*')
                
    return result
