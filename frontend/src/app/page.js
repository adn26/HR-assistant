"use client";
import { useState, useEffect } from "react";

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [jobDescription, setJobDescription] = useState("");
  const [files, setFiles] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidates, setSelectedCandidates] = useState([]);
  const [interviewDate, setInterviewDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [scheduleResult, setScheduleResult] = useState(null);
  const [step, setStep] = useState(1); // 1: JD, 2: Upload, 3: Review, 4: Scheduled

  const API_BASE = "http://localhost:8000";

  useEffect(() => {
    setMounted(true);
  }, []);

  // Submit Job Description
  const handleSubmitJD = async () => {
    if (!jobDescription.trim()) {
      alert("Please enter a job description");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/job_description/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: jobDescription }),
      });

      if (res.ok) {
        alert("Job description saved!");
        setStep(2);
      } else {
        alert("Failed to save job description");
      }
    } catch (error) {
      alert("Error: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Upload Resumes
  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleUploadResumes = async () => {
    if (files.length === 0) {
      alert("Please select resume files");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    try {
      const res = await fetch(`${API_BASE}/upload_resumes/`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        setCandidates(data.candidates || []);
        setStep(3);
      } else {
        alert(data.detail || "Failed to process resumes");
      }
    } catch (error) {
      alert("Error: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Select Candidates
  const toggleCandidateSelection = (id) => {
    setSelectedCandidates((prev) =>
      prev.includes(id) ? prev.filter((cid) => cid !== id) : [...prev, id]
    );
  };

  const selectTopN = (n) => {
    const topIds = candidates.slice(0, n).map((c) => c.id);
    setSelectedCandidates(topIds);
  };

  // Schedule Interviews
  const handleScheduleInterviews = async () => {
    if (selectedCandidates.length === 0) {
      alert("Please select at least one candidate");
      return;
    }

    if (!interviewDate) {
      alert("Please select an interview date");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/select_candidates/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_indices: selectedCandidates,
          interview_date: interviewDate,
          interview_duration: 60,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setScheduleResult(data);
        setStep(4);
      } else {
        alert(data.detail || "Failed to schedule interviews");
      }
    } catch (error) {
      alert("Error: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const resetWorkflow = () => {
    setStep(1);
    setJobDescription("");
    setFiles([]);
    setCandidates([]);
    setSelectedCandidates([]);
    setInterviewDate("");
    setScheduleResult(null);
  };

  if (!mounted) return null;

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.brandRow}>
          <i className="fa-solid fa-bolt" style={styles.brandIcon} />
          <div>
            <h1 style={styles.title}>HR AI Agent</h1>
            <p style={styles.subtitle}>Autonomous recruitment: screening, ranking, and interview scheduling</p>
          </div>
        </div>
      </header>

      {step === 1 && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}><i className="fa-regular fa-file-lines" style={styles.icon} /> Job Description</h2>
          <p style={styles.hintDark}>Paste the job description. This will guide resume parsing and ranking.</p>
          <textarea
            style={styles.textarea}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Enter detailed job description including required skills, experience, education, and responsibilities..."
            rows={12}
          />
          <div style={styles.buttonGroup}>
            <button onClick={handleSubmitJD} disabled={loading} style={styles.primaryButton}>
              {loading ? "Saving..." : <><i className="fa-solid fa-bolt" style={styles.buttonIcon} /> Analyze Job Description →</>}
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}><i className="fa-solid fa-file-arrow-up" style={styles.icon} /> Upload Resumes</h2>
          <p style={styles.hintDark}>Upload one or more PDF resumes for analysis.</p>
          <input type="file" accept=".pdf" multiple onChange={handleFileChange} style={styles.fileInput} />
          {files.length > 0 && (
            <p style={styles.fileCountDark}>✓ {files.length} file{files.length > 1 ? "s" : ""} selected</p>
          )}
          <div style={styles.buttonGroup}>
            <button onClick={() => setStep(1)} style={styles.secondaryButton}>← Back</button>
            <button onClick={handleUploadResumes} disabled={loading || files.length === 0} style={styles.primaryButton}>
              {loading ? "Processing..." : <><i className="fa-solid fa-bolt" style={styles.buttonIcon} /> Process & Rank Candidates →</>}
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}><i className="fa-solid fa-users" style={styles.icon} /> Review Candidates</h2>
          <p style={styles.hintDark}>Candidates are ordered by match score. Select who to schedule.</p>

          <div style={styles.quickActions}>
            <button onClick={() => selectTopN(3)} style={styles.smallButton}>Select Top 3</button>
            <button onClick={() => selectTopN(5)} style={styles.smallButton}>Select Top 5</button>
            <button onClick={() => setSelectedCandidates([])} style={styles.smallButton}>Clear</button>
          </div>

          <div style={styles.candidateList}>
            {candidates.map((candidate, idx) => (
              <div
                key={candidate.id}
                style={{
                  ...styles.candidateCard,
                  ...(selectedCandidates.includes(candidate.id) ? styles.selectedCard : {}),
                }}
                onClick={() => toggleCandidateSelection(candidate.id)}
              >
                <div style={styles.cardHeader}>
                  <div>
                    <h3 style={styles.candidateName}>{idx + 1}. {candidate.name}</h3>
                    <p style={styles.candidateContactDark}><i className="fa-regular fa-envelope" style={styles.icon} /> {candidate.email} | <i className="fa-solid fa-phone" style={styles.icon} /> {candidate.phone}</p>
                  </div>
                  <div style={styles.scoreContainer}>
                    <div style={styles.score}>{candidate.score || 0}</div>
                    <div style={styles.scoreLabel}>Match Score</div>
                  </div>
                </div>

                <div style={styles.candidateDetails}>
                  <p style={{ color: "#222" }}><strong>Experience:</strong> {candidate.experience_years} years</p>
                  <p style={{ color: "#222" }}><strong>Skills:</strong> {candidate.skills?.join(", ") || "N/A"}</p>
                  {candidate.summary && (<p style={styles.summary}><strong>Summary:</strong> {candidate.summary}</p>)}
                  {candidate.recommendation && (
                    <span style={{ ...styles.badge, ...styles[`${candidate.recommendation.replace("_", "")}Badge`] }}>
                      {candidate.recommendation.replace("_", " ").toUpperCase()}
                    </span>
                  )}
                </div>

                {selectedCandidates.includes(candidate.id) && (<div style={styles.checkmark}>✓ Selected</div>)}
              </div>
            ))}
          </div>

          <div style={styles.scheduleSection}>
            <h3><i className="fa-regular fa-calendar" style={styles.icon} /> Select Interview Date</h3>
            <input
              type="date"
              value={interviewDate}
              onChange={(e) => setInterviewDate(e.target.value)}
              min={mounted ? new Date().toISOString().split("T")[0] : undefined}
              style={styles.dateInput}
            />
            <p style={styles.hintDark}>Interviews will be scheduled sequentially from this date.</p>
          </div>

          <div style={styles.buttonGroup}>
            <button onClick={() => setStep(2)} style={styles.secondaryButton}>← Back</button>
            <button onClick={handleScheduleInterviews} disabled={loading || selectedCandidates.length === 0} style={styles.primaryButton}>
              {loading ? "Scheduling..." : <><i className="fa-solid fa-bolt" style={styles.buttonIcon} /> Schedule {selectedCandidates.length} Interview{selectedCandidates.length > 1 ? "s" : ""} →</>}
            </button>
          </div>
        </div>
      )}

      {step === 4 && scheduleResult && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}><i className="fa-solid fa-circle-check" style={styles.icon} /> Interviews Scheduled</h2>
          <p style={styles.successMessage}>{scheduleResult.message}</p>

          <div style={styles.resultList}>
            <h3 style={{ color: "#222" }}><i className="fa-regular fa-calendar" style={styles.icon} /> Scheduled Interviews:</h3>
            {scheduleResult.scheduled_interviews?.map((interview, idx) => (
              <div key={idx} style={styles.resultCard}>
                <h4 style={{ color: "#222" }}>{interview.candidate_name}</h4>
                <p style={{ color: "#222" }}><i className="fa-regular fa-envelope" style={styles.icon} />{interview.candidate_email}</p>
                <p style={{ color: "#222" }}><i className="fa-regular fa-clock" style={styles.icon} />{new Date(interview.interview_start).toLocaleString()}</p>
                <p style={{ color: "#222" }}>
                  <strong>Status:</strong>{" "}
                  <span style={{ color: (interview.status === "scheduled" || interview.status === "scheduled_mock") ? "green" : "red" }}>
                    {interview.status}
                  </span>
                </p>
                {interview.calendar_link && (
                  <a href={interview.calendar_link} target="_blank" rel="noopener noreferrer" style={styles.link}>
                    View in Calendar
                  </a>
                )}
              </div>
            ))}
          </div>

          <div style={styles.resultList}>
            <h3 style={{ color: "#222" }}><i className="fa-regular fa-envelope" style={styles.icon} /> Email Confirmation Status:</h3>
            {scheduleResult.email_status?.map((email, idx) => (
              <div key={idx} style={styles.resultCard}>
                <p style={{ color: "#222" }}>
                  <i className="fa-regular fa-envelope" style={styles.icon} />{email.email}:{" "}
                  <span style={{ color: (email.status === "sent" || email.status === "mock_sent") ? "green" : "red" }}>
                    {email.status}
                  </span>
                </p>
                <p style={styles.hintDark}>{email.message}</p>
              </div>
            ))}
          </div>

          <button onClick={resetWorkflow} style={styles.primaryButton}><i className="fa-solid fa-rotate-right" style={styles.buttonIcon} /> Start New Recruitment</button>
        </div>
      )}
    </div>
  );
}


const styles = {
  container: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "20px",
    fontFamily: "system-ui, -apple-system, sans-serif",
    color: "#222222",
  },
  header: {
    textAlign: "center",
    marginBottom: "30px",
    padding: "20px",
    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    color: "white",
    borderRadius: "12px",
  },
  brandRow: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    justifyContent: "center",
  },
  brandIcon: {
    fontSize: "40px",
    lineHeight: 1,
    marginRight: "12px",
    display: "inline-block",
    verticalAlign: "middle",
  },
  title: {
    margin: 0,
    fontSize: "32px",
    fontWeight: 800,
    letterSpacing: "0.3px",
    color: "#ffffff",
  },
  subtitle: {
    margin: 0,
    marginTop: "4px",
    fontSize: "14px",
    color: "#f0f0f0",
  },
  icon: {
    marginRight: "8px",
    fontSize: "20px",
    verticalAlign: "middle",
  },
  buttonIcon: {
    marginRight: "6px",
    fontSize: "16px",
  },
  title: {
    margin: 0,
    fontSize: "32px",
    fontWeight: 800,
    letterSpacing: "0.3px",
    color: "#ffffff",
  },
  subtitle: {
    margin: 0,
    marginTop: "4px",
    fontSize: "14px",
    color: "#f0f0f0",
  },
  section: {
    background: "white",
    padding: "30px",
    borderRadius: "12px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
    marginBottom: "20px",
  },
  sectionTitle: {
    margin: 0,
    color: "#222222",
    fontSize: "22px",
    fontWeight: 700,
    marginBottom: "8px",
  },
  textarea: {
    width: "100%",
    padding: "15px",
    fontSize: "14px",
    border: "2px solid #e0e0e0",
    borderRadius: "8px",
    marginBottom: "20px",
    fontFamily: "inherit",
    resize: "vertical",
    color: "#222222",
  },
  fileInput: {
    display: "block",
    marginBottom: "15px",
    padding: "10px",
    fontSize: "14px",
  },
  fileCountDark: {
    color: "#2e7d32",
    marginBottom: "15px",
  },
  buttonGroup: {
    display: "flex",
    gap: "10px",
    justifyContent: "flex-end",
  },
  primaryButton: {
    padding: "12px 24px",
    background: "#667eea",
    color: "white",
    border: "none",
    borderRadius: "8px",
    fontSize: "16px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "background 0.3s",
  },
  secondaryButton: {
    padding: "12px 24px",
    background: "#f5f5f5",
    color: "#333",
    border: "none",
    borderRadius: "8px",
    fontSize: "16px",
    fontWeight: "600",
    cursor: "pointer",
  },
  smallButton: {
    padding: "8px 16px",
    background: "#f5f5f5",
    border: "1px solid #ddd",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "14px",
  },
  hintDark: {
    color: "#444",
    fontSize: "14px",
    marginBottom: "15px",
  },
  quickActions: {
    display: "flex",
    gap: "10px",
    marginBottom: "20px",
  },
  candidateList: {
    marginTop: "20px",
  },
  candidateCard: {
    border: "2px solid #e0e0e0",
    borderRadius: "10px",
    padding: "20px",
    marginBottom: "15px",
    cursor: "pointer",
    transition: "all 0.3s",
    position: "relative",
  },
  selectedCard: {
    borderColor: "#667eea",
    background: "#f0f4ff",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "15px",
  },
  candidateName: {
    margin: "0 0 8px 0",
    fontSize: "20px",
    color: "#222",
  },
  candidateContactDark: {
    margin: 0,
    color: "#444",
    fontSize: "14px",
  },
  scoreContainer: {
    textAlign: "center",
  },
  score: {
    fontSize: "32px",
    fontWeight: "bold",
    color: "#667eea",
  },
  scoreLabel: {
    fontSize: "12px",
    color: "#999",
  },
  candidateDetails: {
    fontSize: "14px",
    lineHeight: "1.8",
    color: "#222",
  },
  summary: {
    marginTop: "10px",
    padding: "10px",
    background: "#f9f9f9",
    borderRadius: "6px",
    fontSize: "13px",
    color: "#222",
  },
  badge: {
    display: "inline-block",
    padding: "4px 12px",
    borderRadius: "12px",
    fontSize: "12px",
    fontWeight: "600",
    marginTop: "10px",
  },
  strongfitBadge: {
    background: "#4caf50",
    color: "white",
  },
  goodfitBadge: {
    background: "#8bc34a",
    color: "white",
  },
  moderatefitBadge: {
    background: "#ffc107",
    color: "#333",
  },
  weakfitBadge: {
    background: "#ff9800",
    color: "white",
  },
  checkmark: {
    position: "absolute",
    top: "20px",
    right: "20px",
    background: "#667eea",
    color: "white",
    padding: "5px 15px",
    borderRadius: "20px",
    fontSize: "14px",
    fontWeight: "600",
  },
  scheduleSection: {
    marginTop: "30px",
    padding: "20px",
    background: "#f9f9f9",
    borderRadius: "8px",
  },
  dateInput: {
    padding: "10px",
    fontSize: "16px",
    border: "2px solid #e0e0e0",
    borderRadius: "6px",
    marginBottom: "10px",
    width: "100%",
    maxWidth: "300px",
    color: "#222",
  },
  successMessage: {
    fontSize: "18px",
    color: "#4caf50",
    marginBottom: "30px",
    fontWeight: "500",
  },
  resultList: {
    marginTop: "20px",
  },
  resultCard: {
    background: "#f9f9f9",
    padding: "15px",
    borderRadius: "8px",
    marginBottom: "10px",
  },
  link: {
    color: "#667eea",
    textDecoration: "none",
    fontWeight: "600",
  },
};