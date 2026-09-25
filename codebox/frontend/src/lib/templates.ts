/** Default code for the free-form playground. */
export const PLAYGROUND_TEMPLATES: Record<string, string> = {
  python: `import sys


def main() -> None:
    name = sys.stdin.readline().strip() or "world"
    print(f"Hello, {name}!")


if __name__ == "__main__":
    main()
`,
  javascript: `const input = require("fs").readFileSync(0, "utf8").trim();
const name = input || "world";
console.log(\`Hello, \${name}!\`);
`,
  java: `import java.io.*;

public class Main {
    public static void main(String[] args) throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        String name = in.readLine();
        if (name == null || name.isBlank()) name = "world";
        System.out.println("Hello, " + name.trim() + "!");
    }
}
`,
  cpp: `#include <bits/stdc++.h>
using namespace std;

int main() {
    string name;
    getline(cin, name);
    if (name.empty()) name = "world";
    cout << "Hello, " << name << "!" << '\\n';
}
`,
};
