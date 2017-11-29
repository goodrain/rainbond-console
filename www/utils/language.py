def is_redirect(language, data):
    redirectme = False
    if language == "PHP":
        if data["runtimes"] == "true" and data["dependencies"] == "true" and data["procfile"] == "true":
            redirectme = True
    elif language == "Ruby":
        redirectme = True
    elif language == "Python":
        if data["runtimes"] == "true" and data["dependencies"] == "true":
            redirectme = True
    elif language == "Java-maven":
        if data["runtimes"] == "true":
            redirectme = True
    elif language == "Java-war":
        if data["runtimes"] == "true" and data["procfile"] == "true":
            redirectme = True
    elif language == "Node.js":
        if data["procfile"] == "true":
            redirectme = True
    elif language == "static":
        if data["procfile"] == "true":
            redirectme = True
    elif language == "Clojure":
        redirectme = True
    elif language == "Go":
        redirectme = True
    elif language == "Play":
        redirectme = True
    elif language == "Grails":
        redirectme = True
    elif language == "Scala":
        redirectme = True
    elif language == "Gradle":
        redirectme = True
    return redirectme
