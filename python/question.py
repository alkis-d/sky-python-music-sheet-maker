class Question:

    def __init__(self, question='', information_before='', information_after='', options=None):
        """
        A question object

        Options are for questions where the user chooses from multiple options
        """

        self.information_before = information_before
        self.information_after = information_after
        self.question = question
        self.answer = None
        self.options = options

    def get_information_before(self):
        return self.information_before

    def get_question(self):
        return self.question

    def get_answer(self):
        return self.answer

    def get_options(self):
        return self.options

    def ask(self):

        prompt = self.get_information_before()

        if self.get_options() is not None:
            prompt += '\n'

        for i, option in enumerate(self.get_options()):
            prompt += str(i) + ') '
            prompt += option + '\n'

        prompt += self.get_question()
        return prompt

    def set_answer(self, answer):
        self.answer = answer
        # Do anything involving after
        return self.get_information_after()
