import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.BitSet;

import cc.mallet.pipe.CharSequence2TokenSequence;
import cc.mallet.pipe.FeatureSequence2FeatureVector;
import cc.mallet.pipe.Noop;
import cc.mallet.pipe.Pipe;
import cc.mallet.pipe.SerialPipes;
import cc.mallet.pipe.Target2Label;
import cc.mallet.pipe.TokenSequence2FeatureSequence;
import cc.mallet.pipe.iterator.LineIterator;
import cc.mallet.types.Alphabet;
import cc.mallet.types.FeatureSelection;
import cc.mallet.types.FeatureVector;
import cc.mallet.types.InfoGain;
import cc.mallet.types.Instance;
import cc.mallet.types.InstanceList;
import cc.mallet.types.LabelAlphabet;
import cc.mallet.util.CharSequenceLexer;
import cc.mallet.util.CommandOption;

public class MyFeatureSelection {

	public static void main(String args[]) {
		CommandOption.process(MyFeatureSelection.class, args);

		System.out.println("loading......");
		InstanceList instances = loadInstances();
		System.out.println("pruning......");
		instances = prune(instances);
//		storeInstances(instances);

	}


	private static InstanceList prune(InstanceList instances) {
		Alphabet dict = instances.getDataAlphabet();
		int numFeatures = dict.size();

		BitSet bs = new BitSet(numFeatures);
		bs.set(0, bs.size());
		FeatureSelection fs = new FeatureSelection(dict, bs);
		PrintWriter feature_writer = null;
		try {
			feature_writer = new PrintWriter(new FileWriter(
					outputFeatureFile.valueToString()));
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}

		if (pruneInfogain.wasInvoked() || pruneCount.wasInvoked()) {
			if (pruneCount.value > 0) {
				double[] counts = new double[numFeatures];

				for (int ii = 0; ii < instances.size(); ii++) {
					Instance instance = instances.get(ii);
					FeatureVector fv = (FeatureVector) instance.getData();
					fv.addTo(counts);
				}
				for (int fi = 0; fi < numFeatures; fi++) {
					if (counts[fi] > pruneCount.value) {
						bs.set(fi);
					}
				}
				bs.and(fs.getBitSet());
				fs = new FeatureSelection(dict, bs);
			}

			if (pruneInfogain.value > 0) {
				InfoGain ig = new InfoGain(instances);
				bs.and(new FeatureSelection(ig, pruneInfogain.value)
						.getBitSet());
				fs = new FeatureSelection(dict, bs);
			}
		}

		bs = fs.getBitSet();
		for (int ii = 0; ii < numFeatures; ii++) {
			if (bs.get(ii)) {
				feature_writer.printf("%s\n", dict.lookupObject(ii).toString());
			}
		}
		feature_writer.close();

		Alphabet alpha2 = new Alphabet();
		Noop pipe2 = new Noop(alpha2, instances.getTargetAlphabet());
		InstanceList instances2 = new InstanceList(pipe2);
		for (int ii = 0; ii < instances.size(); ii++) {
			Instance instance = instances.get(ii);
			FeatureVector fv = (FeatureVector) instance.getData();
			FeatureVector fv2 = FeatureVector.newFeatureVector(fv, alpha2, fs);

			instances2.add(
					new Instance(fv2, instance.getTarget(), instance.getName(),
							instance.getSource()), instances
							.getInstanceWeight(ii));
			instance.unLock();
			instance.setData(null); // So it can be freed by the garbage
									// collector
		}
		instances = instances2;
		return instances;
	}

	private static InstanceList loadInstances() {
		Alphabet features = new Alphabet();
		LabelAlphabet labels = new LabelAlphabet();
		Pipe instancePipe = new SerialPipes(new Pipe[] {
				new CharSequence2TokenSequence(new CharSequenceLexer(
						CharSequenceLexer.LEX_NONWHITESPACE_TOGETHER)),
				new Target2Label(labels),
				new TokenSequence2FeatureSequence(features),
				new FeatureSequence2FeatureVector() });

		InstanceList instances = new InstanceList(instancePipe);
		String instanceFormat = "^\\s*(\\S+)\\s*(.*)\\s*$";
		try {
			instances.addThruPipe(new LineIterator(inputFile.valueToString(), instanceFormat, 2,
					1, -1));
		} catch (FileNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return instances;
	}

	static CommandOption.File inputFile = new CommandOption.File(
			MyFeatureSelection.class, "input", "FILE", true, new File("-"),
			"Read the instance list from this file; Using - indicates stdin.",
			null);

	static CommandOption.File outputFile = new CommandOption.File(
			MyFeatureSelection.class,
			"output",
			"FILE",
			true,
			new File("-"),
			"Write pruned instance list to this file (use --training-file etc. if you are splitting the list). Using - indicates stdin.",
			null);

	static CommandOption.File outputFeatureFile = new CommandOption.File(
			MyFeatureSelection.class, "output-feature", "FILE", true, new File(
					"-"), "feature list file", null);

	static CommandOption.Integer pruneInfogain = new CommandOption.Integer(
			MyFeatureSelection.class, "prune-infogain", "N", false, 0,
			"Reduce features to the top N by information gain.", null);

	static CommandOption.Integer pruneCount = new CommandOption.Integer(
			MyFeatureSelection.class, "prune-count", "N", false, 0,
			"Reduce features to those that occur more than N times.", null);
	
}
