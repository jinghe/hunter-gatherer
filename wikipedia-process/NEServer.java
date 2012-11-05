import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.CharBuffer;

public class NEServer {

	ServerSocket serverSocket = null;
	ArticleParser parser = null;
	
	public NEServer(int port){
		parser = new ArticleParser();
		try {
			serverSocket = new ServerSocket(port);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}

	public void run() {
		try {
			System.out.println("Awaiting for connections...");

			Socket socket = serverSocket.accept();
			System.out.println("8853 connected.");

			BufferedReader br = new BufferedReader(new InputStreamReader(
					socket.getInputStream()));
			PrintWriter pw = new PrintWriter(new OutputStreamWriter(
					socket.getOutputStream()));
			
			char [] buffer = new char[10000]; 
			int size = br.read(buffer);
			br.read(buffer);
			String str = new String(buffer, 0, size);
			pw.write(parser.parse(str));
			pw.flush();

			socket.shutdownOutput();
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	public static void main(String[] args) {

		NEServer server = new NEServer(8854);
		while (true) {
			server.run();
		}
	}
}
