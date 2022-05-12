# algo-playground #
*Autodidactic to a fault.*
<br><br>

## Contributors ##
* J. Marchewitz
* S. Gupta
* V. Gadkari
<br><br>

## Instructions ##
* To install the project as a local package
    * Make sure your terminal/CMD's working directory is the algo-playground folder
    * Install the current project as a package with pip **(don't forget the period in the command at the end)**
        * On Windows: "python -m pip install -e ."
        * On macOS: "python3 -m pip install -e ."
* Use the tracked git hooks folder instead of your local copy for necessary hooks
    * From the algo-playground directory, run "git config core.hooksPath hooks"
* To update dependencies later down the line, re-install the package locally as above
* [Create an Alpaca account](https://app.alpaca.markets/signup)
    * Once the account is created, switch your view (top left corner) to the paper trading dashboard instead of live.
    * On the right hand side, click "show" on "Your API keys"
    * Make a copy of the file "alpaca.config.example" from main repository folder and rename it to "alpaca.config"
        * Note that "alpaca.config" is in the .gitignore so your file with your keys should not be committed with the rest of your work. The filename should be greyed out in VS Code
    * Open the new "alpaca.config" file and copy/paste your API key ID and secret key inside of the quotations that say "paste here"
    * Run the python script "scratchpad_example.py" inside of the tests folder, and it should print out your account information without any errors
<br><br>

## Notes and Reminders ##
* There is no main.py anymore, create your scratchpads in tests/
* Don't forget to pull before working
* Download the autoDocstring extension for VS Code, and use (CMD/CTRL) + SHIFT + 2 to generate a docstring for a function automatically
* Run the hook folder config command in the instructions
<br><br>

## Experiments ##
Below is a list of the experiments we have tried with results and insights gained from each one.
