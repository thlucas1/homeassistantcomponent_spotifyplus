# external package imports.
# none

# our package imports.
# none

class STAppMessages:
    """
    A strongly-typed resource class, for looking up localized strings, etc.
    
    Threadsafety:
        This class is fully thread-safe.
    """

    MSG_SERVICE_ARGUMENT_NULL:str = "The '%s' service parameter was not specified for the '%s' service call"
    """
    The '%s' service parameter was not specified for the '%s' service call
    """

    MSG_ARGUMENT_NULL:str = "The '%s' argument was not specified for the '%s' function"
    """
    The '%s' argument was not specified for the '%s' function
    """

    MSG_INTENT_HANDLE_REQUEST:str = "Handling intent request '%s'"
    """
    Handling intent request '%s'
    """

    MSG_INTENT_HANDLE_REQUEST_PARMS:str = "Intent Handler Parameters: `%s`"
    """
    Intent Handler Parameters: `%s`
    """

    MSG_INTENT_HANDLE_REQUEST_SLOTS:str = "Intent Handler Parameters: `%s` (slots)"
    """
    Intent Handler Parameters: `%s` (slots)
    """

    MSG_INTENT_HANDLER_EXCEPTION:str = "Intent handler exception detected for \"%s\": %s"
    """
    Intent handler exception detected for \"%s\": %s
    """

    MSG_INTENT_VALIDATE_SLOTS_EXCEPTION:str = "Slot validation failed for Intent handler method '%s': %s"
    """
    An unhandled exception occurred in Intent handler method '%s'; exception: %s
    """

    MSG_INTENT_HANDLER_REGISTER:str = "Component is registering intent handler: '%s'"
    """
    Component is registering intent handler: '%s'
    """

    MSG_INTENT_HANDLER_RESPONSE:str = "Intent handler response: '%s'"
    """
    Intent handler response: '%s'
    """

    MSG_INTENT_HANDLER_SLOT_INFO:str = "Current slot values for intent: '%s'"
    """
    Current slot values for intent: '%s'
    """

    MSG_INTENT_MATCH_CONSTRAINTS_REQ:str="Intent matching contraints request: '%s'"
    """
    Intent matching contraints request: '%s'
    """

    MSG_INTENT_MATCH_CONSTRAINTS_RSLT:str="Intent matching contraints result: '%s' (isMatch=%s, noMatchReason=%s, noMatchName=%s)"
    """
    Intent matching contraints result: '%s' (isMatch=%s, noMatchReason=%s, noMatchName=%s)
    """

    MSG_INTENT_TARGET_ENTITY_STATE:str="Intent '%s' target entity state: '%s'"
    """
    Intent '%s' target entity state: '%s'
    """

    WARN_INTENT_RESPONSE_TEMPLATE_RENDER_ERROR:str=" \
    SpotifyPlus Intent response render error: \
    Text: \"%s\" \
    Error: %s"

    MSG_SERVICE_CALL_START:str = "Processing service call '%s' in async '%s' method"
    """
    Processing service call '%s' in async '%s' method
    """

    MSG_SERVICE_CALL_PARM:str = "ServiceCall Parameters"
    """
    ServiceCall Parameters
    """

    MSG_SERVICE_CALL_DATA:str = "ServiceCall Data"
    """
    ServiceCall Data
    """

    MSG_SERVICE_REQUEST_REGISTER:str = "Component async_setup is registering async service: '%s'"
    """
    Component async_setup is registering async service: '%s'
    """

    MSG_SERVICE_REQUEST_UNKNOWN:str = "Service request '%s' was not recognized by the '%s' method"
    """
    Service request '%s' was not recognized by the '%s' method
    """

    MSG_SERVICE_REQUEST_EXCEPTION:str = "An unhandled exception occurred in Service request method '%s'; exception: %s"
    """
    An unhandled exception occurred in Service request method '%s'; exception: %s
    """

    MSG_SERVICE_EXECUTE:str = "Executing '%s' service on media player '%s'"
    """
    Executing '%s' service on media player '%s'
    """
    
    MSG_SERVICE_QUERY_WEB_API:str = "Retrieving information from the Spotify Web API"
    """
    Retrieving information from the Spotify Web API
    """

    MSG_MEDIAPLAYER_SERVICE:str = "'%s': MediaPlayer is executing service '%s'"
    """
    '%s': MediaPlayer is executing service '%s'
    """

    MSG_MEDIAPLAYER_SERVICE_WITH_PARMS:str = "'%s': MediaPlayer is executing service '%s' - parameters: %s"
    """
    '%s': MediaPlayer is executing service '%s' - parameters: %s
    """

