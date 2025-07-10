function uploadFile() {
  const input = document.getElementById('fileInput');
  const file = input.files[0];
  const formData = new FormData();
  formData.append("file", file);

  fetch("http://localhost:8000/optimize", {
    method: "POST",
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById('resultBox').textContent = JSON.stringify(data.result, null, 2);
  });
}
