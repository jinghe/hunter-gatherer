import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.PrintWriter;
import java.io.Reader;
import java.util.Random;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Pattern;

import cc.mallet.fst.CRF;
import cc.mallet.fst.CRFOptimizableByLabelLikelihood;
import cc.mallet.fst.CRFTrainerByThreadedLabelLikelihood;
import cc.mallet.fst.CRFTrainerByValueGradients;
import cc.mallet.fst.CRFWriter;
import cc.mallet.fst.MaxLatticeDefault;
import cc.mallet.fst.MultiSegmentationEvaluator;
import cc.mallet.fst.NoopTransducerTrainer;
import cc.mallet.fst.SimpleTagger;
import cc.mallet.fst.TokenAccuracyEvaluator;
import cc.mallet.fst.Transducer;
import cc.mallet.fst.TransducerEvaluator;
import cc.mallet.fst.TransducerTrainer;
import cc.mallet.fst.ViterbiWriter;
import cc.mallet.fst.SimpleTagger.SimpleTaggerSentence2FeatureVectorSequence;
import cc.mallet.optimize.Optimizable;
import cc.mallet.pipe.Pipe;
import cc.mallet.pipe.iterator.LineGroupIterator;
import cc.mallet.types.Alphabet;
import cc.mallet.types.FeatureVector;
import cc.mallet.types.InstanceList;
import cc.mallet.types.Sequence;
import cc.mallet.util.CommandOption;
import cc.mallet.util.MalletLogger;

public class MyTrainTest {
	Pipe p = null;

	public CRF run(InstanceList training, InstanceList testing) {
		// setup:
		// CRF (model) and the state machine
		// CRFOptimizableBy* objects (terms in the objective function)
		// CRF trainer
		// evaluator and writer

		// Logger logger = MalletLogger
		// .getLogger(CRFTrainerByThreadedLabelLikelihood.class.getName());
		// logger.setLevel(Level.SEVERE);
		// logger.getParent().setLevel(Level.SEVERE);

		// model
		CRF crf = new CRF(training.getPipe(), (Pipe) null);
		Pattern forbiddenPat = Pattern.compile(forbiddenOption.value());
		Pattern allowedPat = Pattern.compile(allowedOption.value());
		String startName = crf.addOrderNStates(training, ordersOption.value,
				null, defaultOption.value(), forbiddenPat, allowedPat,
				connectedOption.value());
		for (int i = 0; i < crf.numStates(); i++)
			crf.getState(i).setInitialWeight(Transducer.IMPOSSIBLE_WEIGHT);
		for (int i = 0; i < crf.numStates(); i++)
			crf.getState(i).setInitialWeight(Transducer.IMPOSSIBLE_WEIGHT);
		crf.getState(startName).setInitialWeight(0.0);
		// crf.addStatesForBiLabelsConnectedAsIn(training);
		// crf.addStatesForLabelsConnectedAsIn(training);

		// CRFOptimizableBy* objects (terms in the objective function)
		// objective 1: label likelihood objective
		CRFTrainerByThreadedLabelLikelihood crft = new CRFTrainerByThreadedLabelLikelihood(
				crf, 8);
		crft.setGaussianPriorVariance(10.0);
		crft.setUseSparseWeights(true);
		crft.setUseSomeUnsupportedTrick(false);

		// *Note*: labels can also be obtained from the target alphabet
		Object[] labels = new Object[1];
		for (Object label : training.getTargetAlphabet().toArray()) {
			if (label.toString().startsWith("wiki:")) {
				labels[0] = label;
				break;
			}
		}

		TransducerEvaluator evaluator = new MultiSegmentationEvaluator(
				new InstanceList[] { training, testing }, new String[] {
						"train", "test" }, labels, labels);
		// {
		// @Override
		// public boolean precondition(TransducerTrainer tt) {
		// // evaluate model every 5 training iterations
		// return tt.getIteration() % 50 == 0;
		// }
		// };
		// crft.addEvaluator(evaluator);

		// CRFWriter crfWriter = new CRFWriter("ner_crf.model") {
		// @Override
		// public boolean precondition(TransducerTrainer tt) {
		// // save the trained model after training finishes
		// return tt.getIteration() % Integer.MAX_VALUE == 0;
		// }
		// };
		// crft.addEvaluator(crfWriter);

		boolean converged;
		for (int i = 1; i <= 10; i++) {
			converged = crft.train(training, 50);
			// if (i % 1 == 0 && evaluator != null) // Change the 1 to higher
			// integer to evaluate less often
			// evaluator.evaluate(crft);
			if (converged)
				break;
		}

		CRF model = crft.getCRF();
		evaluator.evaluate(crft);
		crft.shutdown();

		return model;

	}

	public InstanceList load(String path) {
		Reader file = null;
		try {
			file = new FileReader(new File(path));
		} catch (FileNotFoundException e) {
			e.printStackTrace();
		}
		return load(file);
	}

	public InstanceList load(Reader file) {
		InstanceList data = null;

		if (p == null) {
			p = new SimpleTaggerSentence2FeatureVectorSequence();
		}

		p.getTargetAlphabet().lookupIndex(defaultOption.value);
		p.setTargetProcessing(true);
		data = new InstanceList(p);
		data.addThruPipe(new LineGroupIterator(file, Pattern.compile("^\\s*$"),
				true));
		return data;
	}

	public CRF loadModel(String modelPath) {
		CRF crf = null;
		try {
			ObjectInputStream s = new ObjectInputStream(new FileInputStream(
					modelPath));
			crf = (CRF) s.readObject();
			s.close();
			p = crf.getInputPipe();
		} catch (FileNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (ClassNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return crf;
	}

	public static Sequence[] apply(Transducer model, Sequence input, int k) {
		Sequence[] answers;
		if (k == 1) {
			answers = new Sequence[1];
			answers[0] = model.transduce(input);
		} else {
			MaxLatticeDefault lattice = new MaxLatticeDefault(model, input,
					null, 500000);
			answers = lattice.bestOutputSequences(k).toArray(new Sequence[0]);
		}
		return answers;
	}
	
	public void test(InstanceList testData, CRF crf, PrintWriter writer){
		for (int i = 0; i < testData.size(); i++) {
			if(i == 165){
				int iii = 0;
				int jjj = iii;
			}
			Sequence input = (Sequence) testData.get(i).getData();
			Sequence[] outputs = apply(crf, input, 1);
			int k = outputs.length;
			boolean error = false;
			for (int a = 0; a < k; a++) {
				if (outputs[a].size() != input.size()) {
					System.err.println("Failed to decode input sequence "
							+ i + ", answer " + a);
					error = true;
				}
			}
			if (!error) {
				for (int j = 0; j < input.size(); j++) {
					StringBuffer buf = new StringBuffer();
					for (int a = 0; a < k; a++)
						buf.append(outputs[a].get(j).toString())
								.append(" ");
					if(i == 165){
						System.out.println(buf);
					}
					writer.println(buf.toString());
				}
				writer.println();
			}
		}
		writer.close();
	}

	public void test(InstanceList testData, CRF crf, String outPath) {
		try {
			PrintWriter writer = new PrintWriter(new FileWriter(outPath));
			test(testData, crf, writer);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

	static public void main(String args[]) {
		MyTrainTest trainTest = new MyTrainTest();
		String option = args[0];
		if (option.equals("--train-test")) {
			InstanceList training = trainTest.load(args[1]);
			InstanceList test = trainTest.load(args[2]);
			String modelPath = args[3];
			CRF crf = trainTest.run(training, test);
			ObjectOutputStream s;
			try {
				s = new ObjectOutputStream(new FileOutputStream(modelPath));
				s.writeObject(crf);
				s.close();
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
		} else if (option.equals("--test")) {
			CRF crf = trainTest.loadModel(args[2]);
			InstanceList test = trainTest.load(args[1]);
			String outPath = args[3];
			trainTest.test(test, crf, outPath);
		}

	}

	static final CommandOption.String defaultOption = new CommandOption.String(
			SimpleTagger.class, "default-label", "STRING", true, "O",
			"Label for initial context and uninteresting tokens", null);
	private static final CommandOption.IntegerArray ordersOption = new CommandOption.IntegerArray(
			SimpleTagger.class, "orders", "COMMA-SEP-DECIMALS", true,
			new int[] { 1 }, "List of label Markov orders (main and backoff) ",
			null);

	private static final CommandOption.String forbiddenOption = new CommandOption.String(
			SimpleTagger.class, "forbidden", "REGEXP", true, "\\s",
			"label1,label2 transition forbidden if it matches this", null);

	private static final CommandOption.String allowedOption = new CommandOption.String(
			SimpleTagger.class, "allowed", "REGEXP", true, ".*",
			"label1,label2 transition allowed only if it matches this", null);
	private static final CommandOption.Boolean connectedOption = new CommandOption.Boolean(
			SimpleTagger.class, "fully-connected", "true|false", true, true,
			"Include all allowed transitions, even those not in training data",
			null);
}
