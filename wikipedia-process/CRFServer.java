import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.ObjectOutputStream;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.PipedReader;
import java.io.PipedWriter;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.Vector;

import cc.mallet.fst.CRF;
import cc.mallet.types.InstanceList;

public class CRFServer extends Thread {
	ServerSocket serverSocket;
	private List<CRF> m_models;
	private List<MyTrainTest> m_testers;

	public CRFServer(List<MyTrainTest> testers, List<CRF> models, int port) {
		m_testers = testers;
		m_models = models;
		try {
			serverSocket = new ServerSocket(port);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

	List<String> label(MyTrainTest tester, CRF model, InstanceList instances) {
		List<String> labelList = new Vector<String>();
		try {
			PipedReader pipedReader = new PipedReader(200000);
			PipedWriter pipedWriter = new PipedWriter(pipedReader);
			PrintWriter writer = new PrintWriter(pipedWriter);
			
			
			tester.test(instances, model, writer);
			BufferedReader reader = new BufferedReader(pipedReader);
			String line = reader.readLine();
			while (line != null) {
				labelList.add(line);
				line = reader.readLine();
			}
			reader.close();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return labelList;
	}

	List<Set<String>> combineLabels(List<Set<String>> multiLabelList,
			List<String> labelList) {
		if (multiLabelList == null) {
			multiLabelList = new Vector<Set<String>>();
			for (String label : labelList) {
				Set<String> multiLabels = new HashSet<String>();
				multiLabels.add(label);
				multiLabelList.add(multiLabels);
			}
		} else {
			int size = labelList.size();
			for (int i = 0; i < size; i++) {
				multiLabelList.get(i).add(labelList.get(i));
			}
		}
		return multiLabelList;
	}

	private void writeLabels(PrintWriter pw, List<Set<String>> multiLabelList) {
		for (Set<String> multiLabels : multiLabelList) {
			for (String label : multiLabels) {
				pw.printf("%s ", label);
			}
			pw.println();
		}
		pw.flush();
	}

	public void run() {
		try {
			System.out.println("Awaiting for connections...");

			Socket socket = serverSocket.accept();

			System.out.println("connected.");

			BufferedReader br = new BufferedReader(new InputStreamReader(
					socket.getInputStream()));
			br.mark(1000000);
			System.out.println(br.readLine());
			br.reset();

			List<Set<String>> labels = null;
			int testerNum = m_testers.size();
			for (int i = 0; i < testerNum; i++) {
				br.reset();
				MyTrainTest tester = m_testers.get(i);
				InstanceList instances = tester.load(br);
				labels = combineLabels(labels,
						label(tester, m_models.get(i), instances));
			}

			PrintWriter pw = new PrintWriter(new OutputStreamWriter(
					socket.getOutputStream()));
			writeLabels(pw, labels);

			socket.shutdownOutput();
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	static List<File> getModelFiles(String modelDir) {
		List<File> modelFiles = new Vector<File>();

		File folder = new File(modelDir);
		File[] listOfFiles = folder.listFiles();

		for (int i = 0; i < listOfFiles.length; i++) {

			if (listOfFiles[i].isFile()) {
				File file = listOfFiles[i];
				if (file.getName().endsWith(".model")) {
					modelFiles.add(file);
				}
			}
		}
		return modelFiles;
	}

	public static void main(String[] args) {
		String modelDir = args[0];
		List<File> modelFiles = getModelFiles(modelDir);

		List<MyTrainTest> testers = new Vector<MyTrainTest>();
		List<CRF> models = new Vector<CRF>();
		for (File modelFile : modelFiles) {
			MyTrainTest trainTest = new MyTrainTest();
			testers.add(trainTest);
			models.add(trainTest.loadModel(modelFile.getAbsolutePath()));
		}

		CRFServer server = new CRFServer(testers, models, 8855);
		while (true) {
			server.run();
		}
	}
}
