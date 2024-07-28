import React, { useState, useEffect } from 'react';
import axios from 'axios';

const App = () => {
    const [staffId, setStaffId] = useState('');
    const [driverName, setDriverName] = useState('');
    const [staffIdSuggestions, setStaffIdSuggestions] = useState([]);
    const [driverNameSuggestions, setDriverNameSuggestions] = useState([]);

    useEffect(() => {
        if (staffId) {
            axios.get(`/staff-id-autocomplete/?term=${staffId}`)
                .then(response => setStaffIdSuggestions(response.data));
        }
    }, [staffId]);

    useEffect(() => {
        if (staffId) {
            axios.get(`/get-driver-name/?staff_id=${staffId}`)
                .then(response => setDriverName(response.data.driver_name));
        }
    }, [staffId]);

    useEffect(() => {
        if (driverName) {
            axios.get(`/driver-autocomplete/?term=${driverName}`)
                .then(response => setDriverNameSuggestions(response.data));
        }
    }, [driverName]);

    return (
        <div className="container form-container">
            <form method="post">
                <div className="form-row">
                    <div className="form-group col-md-4">
                        <label htmlFor="staff_id">Staff ID</label>
                        <input
                            type="text"
                            id="staff_id"
                            name="staff_id"
                            value={staffId}
                            onChange={(e) => setStaffId(e.target.value)}
                            list="staff_id_list"
                            className="form-control"
                        />
                        <datalist id="staff_id_list">
                            {staffIdSuggestions.map((suggestion, index) => (
                                <option key={index} value={suggestion} />
                            ))}
                        </datalist>
                    </div>
                    <div className="form-group col-md-4">
                        <label htmlFor="driver_name">Driver Name</label>
                        <input
                            type="text"
                            id="driver_name"
                            name="driver_name"
                            value={driverName}
                            onChange={(e) => setDriverName(e.target.value)}
                            list="driver_name_list"
                            className="form-control"
                        />
                        <datalist id="driver_name_list">
                            {driverNameSuggestions.map((suggestion, index) => (
                                <option key={index} value={suggestion} />
                            ))}
                        </datalist>
                    </div>
                    <div className="form-group col-md-4">
                        <label htmlFor="duty_card_no">Duty Card No</label>
                        <input type="text" id="duty_card_no" name="duty_card_no" className="form-control" />
                    </div>
                </div>
                <button type="submit" className="btn btn-success">Submit</button>
            </form>
        </div>
    );
}

export default App;
