
def get_id_from_uri(
    uri:str, 
    ) -> str:
    """
    Get the id portion from a Spotify uri value.
        
    Args:
        uri (str):  
            The Spotify URI value.
            Example: `spotify:track:5v5ETK9WFXAnGQ3MRubKuE`
                
    Returns:
        A string containing the id value.
            
    No exceptions are raised with this method.
    """
    result:str = None
        
    try:
            
        # validations.
        if uri is None or len(uri.strip()) == 0:
            return result

        # get Id from uri value.
        colonCnt:int = uri.count(':')
        if colonCnt == 2:
            idx:int = uri.rfind(':')
            if idx > -1:
                result = uri[idx+1:]

        return result

    except Exception:
            
        return None


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
