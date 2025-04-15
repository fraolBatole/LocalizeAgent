from custom_tools import CountMethods, VariableUsage, FanInFanOutAnalysis, ClassCouplingAnalysis

def test_count_methods():
    # Sample Java source code
    java_code = """
        import java.util.ArrayList;
        import java.util.List;

        package localize_agent.datasets;


        public class InputProcessor {

            private List<String> inputs;
            private String lastProcessedInput;
            private int processCount;

            public InputProcessor() {
                this.inputs = new ArrayList<>();
                this.lastProcessedInput = null;
                this.processCount = 0;
            }

            public void addInput(String input) {
                inputs.add(input);
            }

            public void processInputs() {
                for (String input : inputs) {
                    processInput(input);
                }
            }

            private void processInput(String input) {
                // Simulate processing
                System.out.println("Processing: " + input);
                lastProcessedInput = input;
                processCount++;
            }

            public String getLastProcessedInput() {
                return lastProcessedInput;
            }

            public int getProcessCount() {
                return processCount;
            }

            public void resetProcessor() {
                inputs.clear();
                lastProcessedInput = null;
                processCount = 0;
            }

            public void printAllInputs() {
                System.out.println("All Inputs:");
                for (String input : inputs) {
                    System.out.println(input);
                }
            }

            public void removeInput(String input) {
                inputs.remove(input);
            }

            public void processAndReset() {
                processInputs();
                resetProcessor();
            }

            public void addAndProcess(String input) {
                int a = 1;
                addInput(input);
                processInput(input);
            }

            public void printStatus() {
                System.out.println("Last Processed Input: " + lastProcessedInput);
                System.out.println("Total Process Count: " + processCount);
            }
        }
    """

    try:
        # Instantiate the CountMethods tool
        count_methods_tool = CountMethods()

        # Prepare the input for the tool
        varibale_usage_tool = VariableUsage()

        # get fanin tool
        fan_tool = FanInFanOutAnalysis()

        # get class coupling
        class_coupling_tool = ClassCouplingAnalysis()

        # Run the tool with the sample Java code
        result = count_methods_tool._run(java_code)

        variable_result = varibale_usage_tool._run(java_code)

        fan_result = fan_tool._run(java_code)

        class_coupling_result = class_coupling_tool._run(java_code)

    except Exception as e:
        result = f"Error processing Java source code: {e}"
    # Print the result
    print(result)
    print(variable_result)
    print(fan_result)
    print(class_coupling_result)

# Run the test
if __name__ == "__main__":
    test_count_methods()
