const Mutation = require('../../mutation');

function DTUOperator() {
  this.ID = "DTU";
  this.name = "delegatecall-to-untrusted";
}

// Funzione di supporto per verificare se ci sono delegatecall
function containsDelegateCall(node) {
  if (!node) return false;

  // Controlla se il nodo è una delegatecall
  if (node.memberName === 'delegatecall') {
    return true;
  }

  if (node.type === 'BinaryOperation') {
    return containsDelegateCall(node.right);
  }

  // Controlla se uno degli argomenti contiene una delegatecall
  if (node.arguments) {
    const args = Array.isArray(node.arguments) ? node.arguments : [node.arguments];
    if (args.some(arg => containsDelegateCall(arg))) {
      return true;
    }
  }

  // Ricorsione per controllare l'espressione
  return node.expression ? containsDelegateCall(node.expression) : false;
}

DTUOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    ContractDefinition: (node) => {
      if (node.kind === 'interface' || node.kind === 'library') {
        return;
      }

      if (!node.subNodes || node.subNodes.length === 0) {
        return; // Salta il contratto se non ha subNodes
      }

      // Otteniamo l'inizio e la fine del contratto
      const contractStart = node.subNodes[0].range[0];
      const contractEnd = node.range[1]; // Fine del contratto

      // Identifica i costruttori (sia in stile java-like che con keyword constructor)
      const constructorRanges = [];
      node.subNodes.forEach(sub => {
        if (sub.type === 'FunctionDefinition') {
          // La keyword "constructor" oppure il nome della funzione uguale al nome del contratto
          if (sub.kind === 'constructor' || sub.name === node.name) {
            constructorRanges.push(sub.range);
          }
        }
      });

      let hasDelegateCall = false;

      // Visita le espressioni all'interno del contratto, escludendo quelle che sono all'interno di un costruttore
      visit({
        VariableDeclarationStatement: (node) => {
          // Controlla se il nodo possiede il range
          if (!node.range) return;
          // Verifica se il nodo è contenuto in uno dei costruttori
          const insideConstructor = constructorRanges.some(range => node.range[0] >= range[0] && node.range[1] <= range[1]);
          if (insideConstructor) return;

          if (node.initialValue && containsDelegateCall(node.initialValue)) {
            hasDelegateCall = true;
          }
        },

        ExpressionStatement: (exprNode) => {
          // Controlla se il nodo possiede il range
          if (!exprNode.range) return;
          // Verifica se l'espressione è contenuta in un costruttore
          const insideConstructor = constructorRanges.some(range => exprNode.range[0] >= range[0] && exprNode.range[1] <= range[1]);
          if (insideConstructor) return;

          const exprStart = exprNode.range[0];
          const exprEnd = exprNode.range[1];

          // Controlla se l'espressione è nel range del contratto e contiene una delegatecall
          if (exprStart >= contractStart && exprEnd <= contractEnd && containsDelegateCall(exprNode)) {
            hasDelegateCall = true;
          }
        },
      });

      // Se è stata trovata una delegatecall al di fuori di un costruttore, inietta la mutazione
      if (hasDelegateCall) {
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;

        // Aggiunta di `address delegate;` e `setDelegate` all'inizio del contratto
        const originalContractCode = source.slice(contractStart, contractEnd);
        const mutatedCode =
          `address public delegateAddressDTU;\n` +
          `function setDelegateDTU(address delAddrDTU) public {\n` +
          `\trequire(delAddrDTU != address(0));\n` +
          `\tdelegateAddressDTU = delAddrDTU;\n` +
          `}\n` +
          originalContractCode
          .replace(/(\b\w+)(\.delegate)?\.delegatecall/g, 'delegateAddressDTU.delegatecall')
          .replace(/address\(this\)\.delegatecall\((.*?)\)/g, 'delegateAddressDTU.delegatecall($1)')
          .replace(/require\s*\(\s*(?:address\(this\)\.)?delegate(\.delegate)?\.delegatecall/g, 'require(delegateAddressDTU.delegatecall')
          .replace(/\bbetokenLogic(\.delegate)?\.delegatecall/g, 'delegateAddressDTU.delegatecall');

        mutations.push(new Mutation(file, contractStart, contractEnd, startLine, endLine, originalContractCode, mutatedCode, this.ID));
      }
    },
  });

  return mutations;
};

module.exports = DTUOperator;
