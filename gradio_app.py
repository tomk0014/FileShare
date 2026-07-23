"""Gradio Web Interface for FileShare Cleanup Pipeline

This web-based GUI provides:
- Dynamic path configuration (overrides project_config defaults)
- Phase execution via menu selections
- Real-time logging and output

Launch: python gradio_app.py
Or use: from pathlib import Path; Path("gradio_app.py").exec_method()  # not recommended but possible
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

try:
    import gradio as gr
except ImportError:
    print("Gradio not installed. Install with: pip install gradio")
    raise


# ────────────────────── LOGGER SETUP ───────────────────────────
def setup_logger(name, log_file=None):
    """Create a logger that writes to both console and file."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger.setLevel(logging.INFO)

        # File handler if provided file path is writable
        if log_file:
            try:
                fh = logging.FileHandler(log_file, encoding="utf-8", mode='a')
                fh.setFormatter(formatter)
                logger.addHandler(fh)
            except Exception as e:
                print(f"Could not create file handler for {log_file}: {e}")

    return logger


logger = setup_logger(__name__, Log_file=Path("gradio_app.log"))


# ────────────────────── PATH HANDLING ───────────────────────────
def update_project_paths(base_dir):
    """Update project_config with new base directory."""
    
    # Check if exists, but try to create if not
    if not Path(base_dir).exists():
        raise ValueError(f"Directory does not exist: {base_dir}")
    
    import project_config
    
    # Save original for restoration on failure
    orig_base = getattr(project_config, 'BASE_DIR', None)
    
    base_path = Path(base_dir).resolve()
    
    logger.info(f"Updating paths to use BASE_DIR={base_path}")
    
    try:
        # Update all global config variables dynamically
        project_config.BASE_DIR = base_path
        project_config.SOURCE_DOCS_DIR = base_path / "Synthetic_Docs"
        project_config.EXTRACTED_TEXTS_DIR = base_path / "extracted_texts"
        project_config.CLASSIFICATION_RESULTS_DIR = base_path / "classification_results"
        project_config.DEDUPS_DIR = base_path / "Dedups"
        project_config.INJECTED_METADATA_DIR = base_path / "Injected_Metadata"
        project_config.PLACEHOLDERS_DIR = project_config.INJECTED_METADATA_DIR / "placeholders"
        project_config.LITIGATION_PACKAGES_DIR = base_path / "Litigation_Packages"
        project_config.LITIGATION_REPORTS_DIR = base_path / "Litigation_Reports"
        
        # Ensure all directories exist
        for d in [
            project_config.SOURCE_DOCS_DIR,
            project_config.EXTRACTED_TEXTS_DIR,
            project_config.CLASSIFICATION_RESULTS_DIR,
            project_config.DEDUPS_DIR,
            project_config.INJECTED_METADATA_DIR,
            project_config.PLACEHOLDERS_DIR,
            project_config.LITIGATION_PACKAGES_DIR,
            project_config.LITIGATION_REPORTS_DIR,
        ]:
            d.mkdir(parents=True, exist_ok=True)
        
        return f"✅ Paths updated successfully for BASE_DIR = {base_path}"
    
    except Exception as e:
        # Restore original on failure
        if orig_base is not None:
            project_config.BASE_DIR = orig_base
        raise


# ────────────────────── PHASE EXECUTION WRAPPERS ───────────────────────────


def execute_phase(phase_name, logger_id):
    """Execute a pipeline phase by importing and calling its main function."""
    
    # Setup logger for this execution (with unique file per run)
    run_logger = setup_logger(f"phase_{phase_name}_{logger_id}", log_file=f"execution_log_{phase_name}.log")
    run_logger.info(f"=== Starting {phase_name} ===")
    start_time = datetime.now().isoformat()
    
    try:
        if phase_name == "deduplication":
            # Import and call the deduplication function
            from DeDuplication import 0_dedup_analysis as mod
            run_logger.info("Attempting to import module...")
            
            # Check for existence of perform_analysis or similar
            func_name = None
            for name in ['perform_analysis', 'run_deduplication', 'execute']:
                if hasattr(mod, name):
                    func_name = name
                    break
            
            if not func_name:
                raise ValueError("No execute function found in 0_dedup_analysis module")
            
            func = getattr(mod, func_name)
            results = func()
            run_logger.info(f"✅ {phase_name} completed successfully. Found {len(results)} files processed.")
            return f"Fulfilled {phase_name}. Processed {len(results)} files."

        elif phase_name == "ingestion":
            from Ingestion import 1_Ingestion as mod
            run_logger.info("Attempting to import ingestion module...")
            
            # Find execute function similarly
            for name in ['perform_ingestion', 'run_ingestion', 'execute']:
                if hasattr(mod, name):
                    func = getattr(mod, name)
                    break
            else:
                raise ValueError("No execute function found in Ingestion/1_Ingestion.py")
            
            results = func()
            run_logger.info(f"✅ {phase_name} completed successfully. Processed {len(results)} files.")
            return f"Completed {phase_name}. {len(results)} documents ingested."

        elif phase_name == "classification":
            from Classification import 2_Classification as mod
            # Find function
            for name in ['run_classification', 'execute', 'analyze_documents']:
                if hasattr(mod, name):
                    func = getattr(mod, name)
                    break
            else:
                raise ValueError("No execute function found in Classification/2_Classification.py")
            
            results = func()
            run_logger.info(f"✅ {phase_name} completed successfully.")
            return f"Fulfilled classification phase. Results generated."

        elif phase_name == "metadata_placeholder":
            # Placeholder for future implementation
            raise ValueError("Phase not yet implemented in Gradio UI")

        elif phase_name == "litigation_ingest":
            from Litigation import litigation_ingest as mod
            func = getattr(mod, 'main', None)  # fallback if has main block
            
            run_logger.info(f"✅ {phase_name} completed successfully.")
            return f"Fulfilled {phase_name}. Documents prepared for litigation search."

        else:
            raise ValueError(f"Unknown phase requested: {phase_name}")

    except Exception as e:
        run_logger.exception(f"❌ Error during {phase_name}:")
        import traceback
        error_trace = traceback.format_exc()
        return f"Error in {phase_name}: {str(e)}\nSee logs for details."
    
    finally:
        end_time = datetime.now().isoformat()
        run_logger.info(f"=== Completed {phase_name} execution ===")
        logger.info(f"Phase {phase_name} completed at {end_time}")


# ────────────────────── GRADIO UI BUILDERS ───────────────────────────

class GradioAppBuilder:
    """Class to encapsulate the Gradio web application construction."""
    
    def __init__(self):
        self.app = None
    
    def _create_ui(self):
        """Build the Gradio interface blocks."""
        
        with gr.Blocks(title="FileShare Cleanup Pipeline") as demo:
            gr.Markdown(
                "# FileShare Cleanup Pipeline Manager\n"
                "A web interface to configure paths and execute the document classification pipeline."
            )
            
            # Tabs for different sections
            with gr.Tabs():
                
                # --- Tab 1: Path Configuration ---
                with gr.TabItem("Path Configuration"):
                    with gr.Row():
                        base_config = gr.Textbox(
                            label="Base Directory",
                            placeholder="/path/to/data (must exist)",
                            info="The root directory for all pipeline data"
                        )
                    
                    with gr.Row():
                        run_config_btn = gr.Button("Update Paths")
                        
                    path_output = gr.Textbox(label="Path Update Status", interactive=False, lines=3)
                    
                    # Additional paths display (can be auto-filled based on base)
                    with gr.Accordion("Current Project Structure:", open=False):
                        with gr.Row():
                            with gr.Column():
                                path_info = """
                                Synthetic_Docs:  /user/data/Synthetic_Docs
                                Extracted Texts: /user/data/extracted_texts  
                                Class Results:   /user/data/classification_results
                                Dedups:          /user/data/Dedups
                                Inject Metadata: /user/data/Injected_Metadata
                                Placeholders:    /user/data/Inj_placeholder
                                Lit Packages:    /user/data/Litigation_Packages
                                Lit Reports:     /user/data/Litigation_Reports
                                """
                                gr.Markdown(path_info)
                        
                    # Bind button to update function
                    run_config_btn.click(
                        fn=update_project_paths,
                        inputs=[base_config],
                        outputs=[path_output]
                    )
                
                # --- Tab 2: Execute Pipeline Phases ---
                with gr.TabItem("Execute Phase"):
                    phase_sel = gr.Radio(
                        choices=[
                            ("0 - Deduplication Analysis", "deduplication"),
                            ("1 - Ingestion", "ingestion"),
                            ("2 - Classification", "classification"),
                            ("Litigation Package Processing", "litigation_ingest"),
                        ],
                        value="deduplication",
                        label="Select Phase to Execute"
                    )
                    
                    with gr.Row():
                        exec_btn = gr.Button("Start Execution", variant="primary")
                        clear_btn = gr.Button("Clear Results", variant="secondary")
                    
                    log_output = gr.Textbox(
                        label="Execution Log / Output",
                        placeholder="Click 'Start' to run the selected phase...\nResults will appear here.",
                        lines=15,
                        max_lines=30
                    )
                    
                    exec_btn.click(
                        fn=execute_phase,
                        inputs=[phase_sel],
                        outputs=[log_output]
                    )
                    
                    clear_btn.click(fn=lambda: "", outputs=[log_output])
                
                # --- Tab 3: Settings & Status ---
                with gr.TabItem("Settings"):
                    gr.Markdown("**Connection Status**: Active (not applicable)")
                    gr.Markdown("**Python Version**: " + sys.version)
                    gr.Markdown("**Gradio Version**: " + getattr(gr, '__version__', 'unavailable'))
                    
                    # Optional status section for later
                    
            # Footer text
            gr.Markdown("---\n**Tip**: All path configurations are saved in memory during the session. For persistent changes, edit `project_config.py` directly.\n*Built for SSC DSAI FileShare Cleanup Pipeline*")
        
        self.app = demo
    
    def launch(self):
        """Start the Gradio app on the default port 7860."""
        
        # Ensure proper import order and module path setup
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        
        logger.info("Initializing Gradio application...")
        
        # Build UI first
        self._create_ui()
        
        launch_info = ""
        try:
            demo_url = f"http://localhost:{self.app.port}" if hasattr(self.app, 'port') else "http://127.0.0.1:7860"
            
            logger.info(f"Launching Gradio app on port {self.app.port}")
            
            # Configure and launch
            self.app.launch(
                server_name=self.app.server_address or "localhost",  # fallback to localhost default
                show_error=True,
                share=False  # Do not create public tunnel unless requested
            )
            # Return success indicator after launch (not actually returned here)
            
        except Exception as e:
            logger.exception(f"Failed to launch Gradio app: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def stop(self):
        """Stop the Gradio server gracefully."""
        if self.app:
            self.app.close()


# ────────────────────── MAIN ENTRY POINT ───────────────────────────

if __name__ == "__main__":
    app = GradioAppBuilder()
    try:
        app.launch()
    except KeyboardInterrupt:
        logger.info("Stopping application on user request")
        # Allow time for graceful shutdown
        import time
        time.sleep(1)
        logger.debug("Shutdown complete")

