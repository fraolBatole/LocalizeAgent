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
        addInput(input);
        processInput(input);
    }

    public void printStatus() {
        System.out.println("Last Processed Input: " + lastProcessedInput);
        System.out.println("Total Process Count: " + processCount);
    }
}