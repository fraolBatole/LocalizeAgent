import java.util.*;

public class EnterpriseManagementProcessor {

    // TooManyFields
    private String name;
    private String description;
    private String owner;
    private String department;
    private String region;
    private String country;
    private String city;
    private String status;
    private String priority;
    private String category;

    private int score1;
    private int score2;
    private int score3;
    private int score4;
    private int score5;
    private int score6;
    private int score7;
    private int score8;
    private int score9;
    private int score10;

    private boolean active;
    private boolean approved;
    private boolean archived;
    private boolean deleted;
    private boolean reviewed;

    private List<String> logs = new ArrayList<>();
    private Map<String, Integer> counters = new HashMap<>();

    // High Cyclomatic + NPath Complexity
    public int processRecord(String type, int amount, boolean vip,
                             boolean approved, boolean international,
                             boolean urgent) {

        int result = 0;

        if ("A".equals(type)) {
            if (amount > 1000) {
                if (vip) {
                    result += 100;
                } else {
                    result += 50;
                }
            } else {
                if (approved) {
                    result += 20;
                } else {
                    result += 10;
                }
            }
        } else if ("B".equals(type)) {
            if (international) {
                if (urgent) {
                    result += 80;
                } else {
                    result += 40;
                }
            } else {
                if (amount > 500) {
                    result += 25;
                } else {
                    result += 5;
                }
            }
        } else if ("C".equals(type)) {
            if (vip && approved && urgent) {
                result += 200;
            } else if (vip && approved) {
                result += 150;
            } else if (vip) {
                result += 75;
            } else {
                result += 15;
            }
        } else {
            result = -1;
        }

        return result;
    }

    // ExcessiveMethodLength
    public void generateAnnualReport(List<Integer> data) {

        int total = 0;
        int positive = 0;
        int negative = 0;
        int even = 0;
        int odd = 0;

        for (Integer value : data) {

            total += value;

            if (value > 0) {
                positive++;
            } else if (value < 0) {
                negative++;
            }

            if (value % 2 == 0) {
                even++;
            } else {
                odd++;
            }

            if (value > 1000) {
                logs.add("Very High");
            } else if (value > 500) {
                logs.add("High");
            } else if (value > 100) {
                logs.add("Medium");
            } else {
                logs.add("Low");
            }

            if (value < -1000) {
                logs.add("Critical Negative");
            } else if (value < -500) {
                logs.add("Major Negative");
            } else if (value < 0) {
                logs.add("Minor Negative");
            }
        }

        System.out.println(total);
        System.out.println(positive);
        System.out.println(negative);
        System.out.println(even);
        System.out.println(odd);

        for (String log : logs) {
            System.out.println(log);
        }
    }

    // Many trivial methods -> TooManyMethods
    public void method1() {}
    public void method2() {}
    public void method3() {}
    public void method4() {}
    public void method5() {}
    public void method6() {}
    public void method7() {}
    public void method8() {}
    public void method9() {}
    public void method10() {}
    public void method11() {}
    public void method12() {}
    public void method13() {}
    public void method14() {}
    public void method15() {}
    public void method16() {}
    public void method17() {}
    public void method18() {}
    public void method19() {}
    public void method20() {}

    // GodClass-style mixed responsibilities
    public void sendEmail() {
        System.out.println("Sending email...");
    }

    public void calculatePayroll() {
        System.out.println("Calculating payroll...");
    }

    public void exportCsv() {
        System.out.println("Exporting CSV...");
    }

    public void importCsv() {
        System.out.println("Importing CSV...");
    }

    public void auditSecurity() {
        System.out.println("Auditing security...");
    }

    public void generateInvoice() {
        System.out.println("Generating invoice...");
    }

    public void backupDatabase() {
        System.out.println("Backing up database...");
    }

    public void restoreDatabase() {
        System.out.println("Restoring database...");
    }

    public void processInventory() {
        System.out.println("Processing inventory...");
    }

    public void scheduleJobs() {
        System.out.println("Scheduling jobs...");
    }
}