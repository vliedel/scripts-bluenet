import logging
import traceback


class BaseTestException(Exception):
	pass

class BaseTest:
	"""
	Base class for a test.

	A derived class should implement:
	- get_description()
	- _run()
	"""
	def __init__(self, logger: logging.Logger):
		self.logger = logger

	def get_name(self) -> str:
		"""
		Get the name of this test.

		Can be overridden by derived class.
		"""
		return self.__name__

	def get_description(self) -> str:
		"""
		Get the description of this test.

		Should be overridden by derived class.
		"""
		return "Base for test classes"

	async def run(self) -> bool:
		"""
		Run the test.
		:return: True when the test was passed, False when it failed.
		"""
		try:
			await self._run()
			return True
		except Exception as e:
			# TODO: log instead of print
			print("---------------------------------------- Debug info --------------------------------------------------")
			traceback.print_exc()
			print("------------------------------------------------------------------------------------------------------")
			return False

	async def _run(self):
		"""
		Run the test, raise exception when it fails.

		To be implemented by derived class.
		"""
		raise BaseTestException("Not implemented: _run()")



	def user_action_request(self, text: str):
		"""
		Ask the user to do something, wait for user to say it has been done.
		"""
		print("")
		a = input(f"-> {text} \n   <press enter when done>")
		self.logger.info(text)

	def user_question(self, text: str) -> str:
		"""
		Ask the user a question, and return the user's answer.
		"""
		print("")
		answer = input(f"-> {text}")
		self.logger.info(f"{text} --> {answer}")
		return answer

	class UserQuestionOption:
		def __init__(self, return_value, matches: [str] = None, description: str = None):
			"""
			:param return_value: The value to return when this option is selected.
			:param matches: A list op strings that, when given as input, will select this option.
			:param description: The description of this option.
			"""
			self.matches = matches
			self.return_value = return_value
			self.description = description

	def user_question_options(self, question: str, options: [UserQuestionOption] = None, default_return_value=None):
		"""
		Ask the user to pick an option.
		:param question: The question to ask.
		:param options: A list of user question option.
		:param default_return_value: The return value if none of the options was selected.
		:return: The return value of the selected option, or the default otherwise.
		"""
		if options is None:
			options = [
				BaseTest.UserQuestionOption(True, ["yes", "y"]),
				BaseTest.UserQuestionOption(False, ["no", "n"])
			]
		explanation = False
		i = 1
		for option in options:
			if option.description is not None:
				explanation = True
			if option.matches is None:
				option.matches = [str(i)]
			i += 1

		text = f"-> {question}\n    Please select:"
		if explanation:
			text += "\n"
			for option in options:
				text += f"      {option.matches[0]} {option.description}\n"
		else:
			for option in options:
				text += f" {option.matches[0]} /"
			text = text[0:-2] + "\n"

		print("")
		answer = input(text)
		for option in options:
			if answer in option.matches:
				self.logger.info(f"{question} --> {option.return_value}")
				return option.return_value
		self.logger.info(f"{question} --> {default_return_value}")
		return default_return_value
