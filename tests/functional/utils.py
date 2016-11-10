import time
import tempfile
import subprocess
import os

POSS_WORDS = ['Chicago', 'Boston', 'Dallas', 'Atlanta', 'Denver',
              'Seattle', 'Nashville', 'Baltimore', 'Orlando', 'Cleveland'
]

def enroll_user(sdk, user, pin, all_words_same=False):
    """
    Synchronously enrolls the user with the given username,
    pin and file.  Raises any exception raised.
    """

    enroll_rec = sdk.enrollment_start(user, pin=pin)

    anim_words = [
        er['display']
        for er in enroll_rec['animation']
        if er['display'] in POSS_WORDS
    ]

    # Make all words the same for bad enrollment data
    if all_words_same:
        anim_words = [anim_words[0]] * len(POSS_WORDS)

    audio_file = _words_list_to_file(anim_words)

    sdk.enrollment_upload(
        enroll_rec['enrollment_id'],
        audio_file
    )

    os.remove(audio_file)
    # Wait for enrollment to finish
    while True:
        enroll_info = sdk.enrollment_resource(
            enroll_rec['enrollment_id']
        )

        if(enroll_info['state'] == "completed" or
           enroll_info['state'] == "error"):
            break

        time.sleep(0.1)

    if enroll_info['state'] == "error":
        raise RuntimeError(
            "Received error on enrollment: %s" % enroll_info['error']
        )

    time.sleep(5) # Try to avoid rate limiting

def enroll_without_exception(sdk, user, pin):
    """
    Tries to enroll the user and hides the exception if its already enrolled
    """

    try:
        enroll_user(sdk, user, pin)
    except Exception as ex:
        if "Client already enrolled" not in str(ex):
            raise ex



# ----------------------------------------------------------------------------


def uneroll_user(sdk, user):

    sdk.client_unenroll(user)
    while True:
        client_info = sdk.client_info(user)

        if client_info['state'] == "deleted":
            break

        time.sleep(0.1)

# ---------------------------------------------------------------------------

def unenroll_without_exception(sdk, user):
    try:
        uneroll_user(sdk, user)
    except Exception as ex:
        if "Client not enrolled" not in str(ex):
            raise ex

    time.sleep(2) # Try to avoid rate limiting

# ----------------------------------------------------------------------------


def verify_audiopass(sdk, user, num_words_wrong=0):
    """
    Synchronously enrolls the user with the given username,
    pin and file.  Raises any exception raised.
    """

    ver_rec = sdk.verification_start(
        user,
        0, # speed
        "off" # row doubling
    )

    anim_words = [
        er['display']
        for er in ver_rec['animation']
        if er['display'] in POSS_WORDS
    ]

    # Change the words according to the number that are supposed
    # to be wrong.  Canoncially changed to poss_words[0] and [1]
    for i in range(num_words_wrong):
        if anim_words[i] == POSS_WORDS[0]:
            anim_words[i] = POSS_WORDS[1]
        else:
            anim_words[i] = POSS_WORDS[0]

    audio_file = _words_list_to_file(anim_words)

    sdk.verification_upload(
        ver_rec['verification_id'],
        audio_file=audio_file
    )
    os.remove(audio_file)

    # Wait for verification response
    while True:
        ver_info = sdk.verification_resource(
            ver_rec['verification_id']
        )

        if(ver_info['state'] == "completed" or
           ver_info['state'] == "error"):
            break

        time.sleep(0.1)

    if ver_info['state'] == "completed":
        # It was rejected
        rr = ver_info['rejection_reason']
        if rr is not None:
            return rr
        else:
            return "Verified"
    elif ver_info['state'] == "error":
        raise RuntimeError(ver_info['error'])
    else:
        raise RuntimeError("Have a state of %s" % ver_info['state'])


    time.sleep(3) # Try to avoid rate limiting

def _words_list_to_file(anim_words):
    """
    Creates an audio file from the words specified in the given list
    """
    _, out_file = tempfile.mkstemp(suffix=".mp3")

    anim_files = [os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "audio",
        word.lower() + ".mp3"
        )
        for word in anim_words
    ]

    # Lets try using sox for now to avoid numpy dependendencies
    command = "sox {} {}".format(
        " ".join(anim_files),
        out_file
    )

    subprocess.call(command, shell=True)

    return out_file
