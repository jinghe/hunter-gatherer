import java.io.BufferedReader;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringReader;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import edu.stanford.nlp.ie.AbstractSequenceClassifier;
import edu.stanford.nlp.ie.crf.CRFClassifier;
import edu.stanford.nlp.ling.CoreAnnotations.NamedEntityTagAnnotation;
import edu.stanford.nlp.ling.CoreAnnotations.PartOfSpeechAnnotation;
import edu.stanford.nlp.ling.CoreAnnotations.SentencesAnnotation;
import edu.stanford.nlp.ling.CoreAnnotations.TextAnnotation;
import edu.stanford.nlp.ling.CoreAnnotations.TokensAnnotation;
import edu.stanford.nlp.ling.CoreLabel;
import edu.stanford.nlp.ling.Sentence;
import edu.stanford.nlp.ling.TaggedWord;
import edu.stanford.nlp.ling.HasWord;
import edu.stanford.nlp.ling.CoreAnnotations.AnswerAnnotation;
import edu.stanford.nlp.pipeline.Annotation;
import edu.stanford.nlp.pipeline.StanfordCoreNLP;
import edu.stanford.nlp.tagger.maxent.MaxentTagger;
import edu.stanford.nlp.util.CoreMap;

public class ArticleParser {
	StanfordCoreNLP pipeline;

	public ArticleParser() {
		// creates a StanfordCoreNLP object, with POS tagging, lemmatization,
		// NER
		Properties props = new Properties();
		props.put("annotators", "tokenize, ssplit, pos, lemma, ner");
		pipeline = new StanfordCoreNLP(props);

	}

	public String parse(String text) {
		StringBuffer buffer = new StringBuffer();

		// create an empty Annotation just with the given text
		Annotation document = new Annotation(text);

		// run all Annotators on this text
		pipeline.annotate(document);

		// these are all the sentences in this document
		// a CoreMap is essentially a Map that uses class objects as keys and
		// has values with custom types
		List<CoreMap> sentences = document.get(SentencesAnnotation.class);

		for (CoreMap sentence : sentences) {
			// traversing the words in the current sentence
			// a CoreLabel is a CoreMap with additional token-specific methods
			for (CoreLabel token : sentence.get(TokensAnnotation.class)) {
				// this is the text of the token
				String word = token.get(TextAnnotation.class);
				// this is the POS tag of the token
				String pos = token.get(PartOfSpeechAnnotation.class);
				// this is the NER label of the token
				String ne = token.get(NamedEntityTagAnnotation.class);
				buffer.append(word + "/[" + pos + ',' + ne + "] ");
			}
			buffer.append("\n");
		}

		return buffer.toString();

	}

	void parse_file(String inPath, String outPath) {
		try {
			BufferedReader reader = new BufferedReader(new FileReader(
					inPath));
			PrintWriter writer = new PrintWriter(new FileWriter(outPath));
			StringBuffer buffer = new StringBuffer();
			String line = reader.readLine();
			while (line != null) {
				buffer.append(line);
				buffer.append('\n');
				line = reader.readLine();		
			}
			reader.close();
			
			writer.write(parse(buffer.toString()));
			writer.close();
		} catch (FileNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} finally {

		}
	}

	
	static void do_batch_trec(ArticleParser parser, String text_article_path,
			String out_path) {
		int count = 0;
		long t0 = System.currentTimeMillis();
		try {
			BufferedReader reader = new BufferedReader(new FileReader(
					text_article_path));
			PrintWriter writer = new PrintWriter(new FileWriter(out_path));
			StringBuffer buffer = new StringBuffer();
			String line = reader.readLine();
			while (line != null) {
				if (line.startsWith("<")) {
					if (line.startsWith("</DOC")) {
						writer.write(parser.parse(buffer.toString()));
						writer.write('\n');
						buffer = new StringBuffer();
						count ++ ;
						if (count % 10 == 0){
							System.out.printf("%d %f\n", count, (System.currentTimeMillis() - t0) / 1000.0);
						}
					} 
					writer.write(line + '\n');
				} else {
					buffer.append(line + '\n');
				}
				line = reader.readLine();
			}
			reader.close();
			writer.close();
		} catch (FileNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} finally {

		}
	}

	
	
	static public void main(String[] args) {
		String option = args[0];
		ArticleParser parser = new ArticleParser();
		if (option.equals("--test")) {
			parser.parse("Good afternoon Rajat Raina, how are you today? I go to school at Stanford University, which is located in California and was founded in 1834.");
		} else if (option.equals("--batch-trec")) {
			String text_article_path = args[1];
			String out_path = args[2];
			do_batch_trec(parser, text_article_path, out_path);
		} else if (option.equals("--parse-text")){
			String inPath = args[1];
			String outPath = args[2];
			parser.parse_file(inPath, outPath);
		}
	}
}
