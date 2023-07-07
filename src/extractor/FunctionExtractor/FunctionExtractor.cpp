//===--------------------------FunctionExtractor.cpp------------------------===
//
//
//Author: Breno Campos [brenosfg@dcc.ufmg.br | brenocfg@gmail.com]
//
//===-----------------------------------------------------------------------===
//
//Function Extractor is a plugin developed for the Clang compiler frontend.
//Its job is to parse C input files, and extract each individual function
//definition found in them, and externalize them to a single file on their own.
//Note that we extract only function _definitions_, with a body. We simply
//ignore function declarations (and system functions that come from library
//headers).
//
//Function Extractor will write an output file for each function found in the
//input, in the format "extr_filename_funcname.c", where filename is the file
//from which the function was originally extracted.
//
//The plugin can also be used to collect entire files, rather than single
//functions. If configured to run in this way, the plugin instead aggregates
//all function definitions found within a single source file, and outputs
//a file containing all of them together.
//
//Since it is a small self-contained plugin (not meant to be included by other
//applications), all the code is kept within its own source file, for simplici-
//ty's sake.
//
//By default, the plugin is built alongside an LLVM+Clang build, and its shared
//library file (libFunctionExtractor.so) can be found in the /lib/ folder
//within the LLVM build folder.
//
//The plugin can be set to run during any Clang compilation command, using the
//following syntax:
//
// clang -cc1 -load $EXTR -plugin extract-funcs
//
// Where $EXTR -> points to the libFunctionExtractor.so library file location 
//===-----------------------------------------------------------------------===

#include "clang/Driver/Options.h"
#include "clang/AST/AST.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/ASTConsumer.h"
#include "clang/AST/Mangle.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/Frontend/ASTConsumers.h"
#include "clang/Frontend/FrontendActions.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendPluginRegistry.h"
#include "clang/Rewrite/Core/Rewriter.h"

#include <fstream>

using namespace std;
using namespace clang;
using namespace llvm;

/*returns whether a function should be extracted or not*/
static bool shouldExtractFunction(FunctionDecl *D, const SourceManager &mng) {
	/*ignore system functions*/
	if (mng.isInSystemHeader(D->getLocation())) {
		return false;
	}

	/*we want _definitions_, not declarations*/
	if (!D->isThisDeclarationADefinition()) {
		return false;
	}

	return true;
}

/*returns valid filename for an input file*/
static string validateFilename(string originalName) {
	if (originalName.empty()) {
		return "unknown";
	}

	string ret;
	for (char &c : originalName) {
		if (c == '/') {
			continue;
		}
		ret += c;
	}

	return ret;
}

/*This is the AST visitor we use to collect functions for whole files. It
traverses the AST finding every function definition and aggregates them into
a single output file, then prints it.*/
class WholeFileVisitor : public RecursiveASTVisitor<WholeFileVisitor> {
private:
	ASTContext *astContext;
	//MangleContext *mangleContext;
	string _outFileName;
	string _output;

public:
explicit WholeFileVisitor(CompilerInstance *CI, StringRef file)
	: astContext(&(CI->getASTContext())) {
		_outFileName = file.str();
		_outFileName = validateFilename("extr_wholefile_" + _outFileName);
	}
	
	/*visits all Function Declaration nodes*/
	virtual bool VisitFunctionDecl(FunctionDecl *D) {
		const SourceManager &mng = astContext->getSourceManager();
		const LangOptions &LO = astContext->getLangOpts();
		Rewriter Extractor(astContext->getSourceManager(), LO);

		/*ignore functions that are not of interest (returning true resumes
		AST traversal*/
		if (!shouldExtractFunction(D, mng)) {
			return true;
		}

		string funcName = D->getNameInfo().getName().getAsString();
		/*let's not extract functions with weird names that mess up filename*/
		if (funcName == "_") {
			return true;
		}

		outs() << "[Function Extractor plugin] Processing Function: " << 
															funcName << "\n";

		string funcBody = Extractor.getRewrittenText(D->getSourceRange());
		/*some functions have empty bodies for some reason, skip them*/
		if (funcBody.empty()) {
			return true;
		}

		/*we inject a ((used)) attribute before static functions, because Clang
		does not generate bytecode for unused static functions*/
		if (D->getStorageClass() == SC_Static) {
			funcBody = "__attribute__((used)) " + funcBody;
		}

		/*append function definition to output file*/
		_output += funcBody + "\n\n";

		return true;
	}

	void printOutput() {
		ofstream outfile;
		outfile.open(_outFileName);

		if (!outfile.is_open()) {
			errs()<<"[Function Extractor plugin] Error creating output file!\n";
			return;
		}

		outfile << _output;
		outfile.close();
	}
};

/*This is the AST visitor we use to collect single functions. It traverses the
AST and, for every function definition, creates a single file with the
function's contents and outputs it.*/
class FunctionVisitor : public RecursiveASTVisitor<FunctionVisitor> {
private:
	ASTContext *astContext; //provides AST context info
	//MangleContext *mangleContext; //for C++ name mangling

public:
	explicit FunctionVisitor(CompilerInstance *CI) 
	  : astContext(&(CI->getASTContext())) {}

	/*visits all Function Declaration nodes*/
	virtual bool VisitFunctionDecl(FunctionDecl *D) {
		const SourceManager &mng = astContext->getSourceManager();
		const LangOptions &LO = astContext->getLangOpts();
		Rewriter Extractor(astContext->getSourceManager(), LO);

		/*ignore functions that are not of interest (returning true resumes
		AST traversal*/
		if (!shouldExtractFunction(D, mng)) {
			return true;
		}

		string inputFile;
		string funcName;
		string outfileName;

		/*open output file, format: "extr_originfile_functionname.c"*/
		inputFile = validateFilename(mng.getFilename(D->getSourceRange().getBegin()).str());
		funcName = D->getNameInfo().getName().getAsString();
		outfileName = "extr_" + inputFile + "_" + funcName + ".c";
		
		/*let's not extract functions with weird names that mess up filename*/
		if (funcName == "_") {
			return true;
		}

		outs() << "[Function Extractor plugin] Processing Function: " << 
								funcName << ", File: " << inputFile << "\n";

		string funcBody = Extractor.getRewrittenText(D->getSourceRange());
		/*some functions have empty bodies for some reason, skip them*/
		if (funcBody.empty()) {
			return true;
		}

		/*we inject a ((used)) attribute before static functions, because Clang
		does not generate bytecode for unused static functions*/
		if (D->getStorageClass() == SC_Static) {
			funcBody = "__attribute__((used)) " + funcBody;
		}

		ofstream outFile;
		outFile.open(outfileName);

		if (!outFile.is_open()) {
			errs() << "[Function Extractor plugin] Error creating file " <<
														outfileName << "!\n";
		}


		/*output function text to file*/
		outFile << funcBody; 
		outFile.close();

		return true;
	}
};



class FunctionASTConsumer : public ASTConsumer {
private:
	FunctionVisitor *fvisitor; 

public:
	/*override the constructor in order to pass CI*/
	explicit FunctionASTConsumer(CompilerInstance *CI, StringRef file)
		: fvisitor(new FunctionVisitor(CI)) {}

	/*we override HandleTranslationUnit so it calls our visitor
	after parsing each entire input file*/
	virtual void HandleTranslationUnit(ASTContext &Context) {
		/*traverse the AST*/
		fvisitor->TraverseDecl(Context.getTranslationUnitDecl());
	}
};


class WholeFileASTConsumer : public ASTConsumer {
private:
	WholeFileVisitor *wfvisitor;

public:
	/*override the constructor in order to pass CI*/
	explicit WholeFileASTConsumer(CompilerInstance *CI, StringRef file)
		:  wfvisitor(new WholeFileVisitor(CI, file)) {}

	/*we override HandleTranslationUnit so it calls our visitor
	after parsing each entire input file*/
	virtual void HandleTranslationUnit(ASTContext &Context) {
		/*traverse the AST*/
		wfvisitor->TraverseDecl(Context.getTranslationUnitDecl());
		wfvisitor->printOutput();
	}
};

class FunctionPluginAction : public PluginASTAction {
private:
	bool whole_file = false;
protected:
	unique_ptr<ASTConsumer> CreateASTConsumer(CompilerInstance &CI, 
											  StringRef file) {
		if (whole_file) {
			return std::make_unique<WholeFileASTConsumer>(&CI, file);
		}
		else {
			return std::make_unique<FunctionASTConsumer>(&CI, file);
		}
	}

	bool ParseArgs(const CompilerInstance &CI, const vector<string> &args) {
		for (auto &arg : args) {
			if (arg == "-whole-files") {
				whole_file = true;
			}
		}
		return true;
	}
};

/*register the plugin and its invocation command in the compilation pipeline*/
static FrontendPluginRegistry::Add<FunctionPluginAction> X
									("extract-funcs", "Function Extractor");
