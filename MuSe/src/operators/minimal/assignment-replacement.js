// Import the Mutation class from the specified module
const Mutation = require("../../mutation");

/**
 * This script defines an Assignment Operator Replacement (AOR) mutation operator.
 * Its purpose is to generate mutated versions of source code by replacing assignment
 * operators (such as +=, -=, *=, /=, etc.) with other operators. These mutations are
 * useful for testing the robustness of software by introducing deliberate changes
 * and observing how the software responds. This process helps in identifying potential
 * weaknesses and improving code quality. The script uses a visitor pattern to traverse
 * the abstract syntax tree (AST) of the source code, locates binary operation nodes,
 * and performs the specified replacements to generate new code variants.
 */

// Define the AOROperator class
function AOROperator() {
  this.ID = "AOR"; // Identifier for the mutation type
  this.name = "assignment-operator-replacement"; // Name of the mutation type
}

// Method to get mutations for a given file and source code
AOROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = []; // Array to store generated mutations

  // Visit each binary operation node in the source code
  visit({
    BinaryOperation: (node) => {
      // Determine the start and end positions of the operator in the source code
      const start = node.left.range[1] + 1;
      const end = node.right.range[0];
      const startLine = node.left.loc.end.line;
      const endLine = node.right.loc.start.line;
      const original = source.slice(start, end); // Extract the original operator
      let replacement, replacement2;

      // Switch statement to handle different assignment operators
      switch (node.operator) {
        case "+=":
          replacement = original.replace("+=", "-="); // Replace "+=" with "-="
          replacement2 = original.replace("+=", " ="); // Replace "+=" with "="
          break;
        case "-=":
          replacement = original.replace("-=", "+="); // Replace "-=" with "+="
          replacement2 = original.replace("-=", " ="); // Replace "-=" with "="
          break;
        case "*=":
          replacement = original.replace("*=", "/="); // Replace "*=" with "/="
          replacement2 = original.replace("*=", " ="); // Replace "*=" with "="
          break;
        case "/=":
          replacement = original.replace("/=", "*="); // Replace "/=" with "*="
          replacement2 = original.replace("/=", " ="); // Replace "/=" with "="
          break;
        case "%=":
          replacement = original.replace("%=", "*="); // Replace "%=" with "*="
          replacement2 = original.replace("%=", " ="); // Replace "%=" with "="
          break;
        case "<<=":
          replacement = original.replace("<<=", ">>="); // Replace "<<=" with ">>="
          replacement2 = original.replace("<<=", " ="); // Replace "<<=" with "="
          break;
        case ">>=":
          replacement = original.replace(">>=", "<<="); // Replace ">>=" with "<<="
          replacement2 = original.replace(">>=", " ="); // Replace ">>=" with "="
          break;
        case "|=":
          replacement = original.replace("|=", "&="); // Replace "|=" with "&="
          replacement2 = original.replace("|=", " ="); // Replace "|=" with "="
          break;
        case "&=":
          replacement = original.replace("&=", "|="); // Replace "&=" with "|="
          replacement2 = original.replace("&=", " ="); // Replace "&=" with "="
          break;
        case "^=":
          replacement = original.replace("^=", "&="); // Replace "^=" with "&="
          replacement2 = original.replace("^=", " ="); // Replace "^=" with "="
          break;
      }

      // Add the mutations to the mutations array
      if (replacement)
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
      if (replacement2)
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement2, this.ID));
    }
  });

  return mutations; // Return the array of mutations
};

// Export the AOROperator module
module.exports = AOROperator;
